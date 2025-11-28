import logging
import os
import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, layers
from tensorflow.keras.optimizers import Adam

from core.model_registry import ModelMetadata, ModelRegistry

from .data_processing import DataTransformer
from .feature_engineer import FeatureEngineer
from .kairos import Kairos
from .schemas import ScheduleRequest


class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.buffer: list[tuple[np.ndarray, int, float, Optional[np.ndarray], bool]] = (
            []
        )
        self.position = 0
        self.logger = logging.getLogger(__name__ + ".ReplayBuffer")

    def add(
        self,
        state: np.ndarray,
        action_index: int,
        reward: float,
        next_state: Optional[np.ndarray],
        done: bool,
    ) -> None:
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action_index, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> Tuple[
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
        Optional[np.ndarray],
    ]:
        num_samples_in_buffer = len(self.buffer)
        actual_batch_size = min(batch_size, num_samples_in_buffer)

        if actual_batch_size == 0:
            self.logger.warning(
                "Sample requested from empty or insufficiently filled buffer."
            )
            return None, None, None, None, None

        batch_indices = np.random.choice(
            num_samples_in_buffer, actual_batch_size, replace=False
        )
        states, actions, rewards, next_states_raw, dones = zip(
            *[self.buffer[i] for i in batch_indices]
        )

        # Handle None in next_states if episodes ended
        # Assuming states[0] is a valid state, to get its shape for zero padding
        zero_state_example = np.zeros_like(states[0]) if states else np.array([])
        valid_next_states = [
            ns if ns is not None else zero_state_example for ns in next_states_raw
        ]

        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int32),
            np.array(rewards, dtype=np.float32),
            np.array(valid_next_states, dtype=np.float32),
            np.array(dones, dtype=bool),
        )

    def __len__(self) -> int:
        return len(self.buffer)

    def save_buffer(self, filepath: Path) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(filepath, "wb") as f:
                pickle.dump(self.buffer, f)
            self.logger.info(
                f"Replay buffer content (size {len(self)}) saved to {filepath}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to save replay buffer to {filepath}: {e}", exc_info=True
            )

    def load_buffer(self, filepath: Path) -> None:
        if filepath.exists() and filepath.is_file():
            try:
                with open(filepath, "rb") as f:
                    self.buffer = pickle.load(f)
                self.position = (
                    len(self.buffer) % self.capacity
                    if self.capacity > 0 and self.buffer
                    else 0
                )
                self.logger.info(
                    f"Replay buffer content loaded from {filepath}. Size: {len(self.buffer)}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to load replay buffer from {filepath}: {e}. Starting with an empty buffer.",
                    exc_info=True,
                )
                self.buffer = []
                self.position = 0
        else:
            self.logger.warning(
                f"Replay buffer file not found at {filepath}. Starting with an empty buffer."
            )
            self.buffer = []
            self.position = 0


class AIScheduler:
    def __init__(
        self,
        kairos_instance: Kairos,
        data_transformer: DataTransformer,
        feature_engineer: FeatureEngineer,
        model_base_dir: Path = Path("models"),
        actor_lr: float = 0.0003,
        critic_lr: float = 0.001,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        policy_clip: float = 0.2,
        entropy_coefficient: float = 0.01,
        epochs_per_update: int = 10,
        ppo_batch_size: int = 64,
        replay_buffer_capacity: int = 10000,
    ):
        self.kairos_instance = kairos_instance
        self.data_transformer = data_transformer
        self.feature_engineer = feature_engineer
        self.input_dim = feature_engineer.EXPECTED_FEATURE_DIM

        self.output_dim = len(self.kairos_instance.list_strategies())
        self.strategy_names = self.kairos_instance.list_strategies()

        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.policy_clip = policy_clip
        self.entropy_coefficient = entropy_coefficient
        self.epochs_per_update = epochs_per_update
        self.ppo_batch_size = ppo_batch_size

        # Models
        self.actor = self._build_actor_model()
        self.critic = self._build_critic_model()
        self.actor_optimizer = Adam(learning_rate=actor_lr)
        self.critic_optimizer = Adam(learning_rate=critic_lr)

        self.replay_buffer = ReplayBuffer(capacity=replay_buffer_capacity)
        self.logger = logging.getLogger(__name__)

        # State & Paths
        self.model_base_dir = Path(model_base_dir)
        self.model_base_dir.mkdir(parents=True, exist_ok=True)

        # TensorBoard
        self.log_dir = self.model_base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.summary_writer = tf.summary.create_file_writer(str(self.log_dir))
        self.global_train_step = 0

        # Identifier for the currently active model (e.g. "v1_production")
        self.current_model_name = self.model_base_dir.name

        # Initial Load
        self.load_models()

    def _build_actor_model(self) -> Model:
        """Builds the Actor (Policy) network."""
        inputs = layers.Input(shape=(self.input_dim,))
        x = layers.Dense(128, activation="relu", kernel_initializer="he_uniform")(
            inputs
        )
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(64, activation="relu", kernel_initializer="he_uniform")(x)
        x = layers.Dropout(0.2)(x)
        outputs = layers.Dense(max(self.output_dim, 2), activation="softmax")(x)
        model = Model(inputs=inputs, outputs=outputs, name="actor")
        return model

    def _build_critic_model(self) -> Model:
        """Builds the Critic (Value) network."""
        inputs = layers.Input(shape=(self.input_dim,))
        x = layers.Dense(128, activation="relu", kernel_initializer="he_uniform")(
            inputs
        )
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(64, activation="relu", kernel_initializer="he_uniform")(x)
        x = layers.Dropout(0.2)(x)
        outputs = layers.Dense(1, activation=None)(x)
        model = Model(inputs=inputs, outputs=outputs, name="critic")
        return model

    def get_actor_save_path(self) -> Path:
        return self.model_base_dir / "ai_scheduler_actor_weights.weights.h5"

    def get_critic_save_path(self) -> Path:
        return self.model_base_dir / "ai_scheduler_critic_weights.weights.h5"

    def _get_weights_paths(self, base_dir: Path = None) -> Tuple[Path, Path]:
        """Helper to get standard file paths for a given directory."""
        target_dir = base_dir if base_dir else self.model_base_dir
        return (
            target_dir / "ai_scheduler_actor_weights.weights.h5",
            target_dir / "ai_scheduler_critic_weights.weights.h5",
        )

    def save_models(self) -> None:
        """Saves current weights to the configured model_base_dir."""
        actor_path, critic_path = self._get_weights_paths()
        try:
            self.actor.save_weights(str(actor_path))
            self.critic.save_weights(str(critic_path))
            self.logger.info(f"Models saved to {self.model_base_dir}")
        except Exception as e:
            self.logger.error(f"Error saving models: {e}", exc_info=True)

    def load_models(self, specific_dir: Path = None) -> bool:
        """
        Loads weights. If specific_dir is provided, loads from there.
        Otherwise loads from self.model_base_dir.
        """
        target_dir = specific_dir if specific_dir else self.model_base_dir
        actor_path, critic_path = self._get_weights_paths(target_dir)

        # We must call the models once to initialize weights before loading
        dummy = np.zeros((1, self.input_dim), dtype=np.float32)
        self.actor(dummy)
        self.critic(dummy)

        success = True
        if actor_path.exists():
            try:
                self.actor.load_weights(str(actor_path))
                self.logger.info(f"Loaded Actor from {actor_path}")
            except Exception as e:
                self.logger.error(f"Failed to load Actor: {e}")
                success = False
        else:
            self.logger.warning(f"No Actor weights found at {actor_path}")
            success = False

        if critic_path.exists():
            try:
                self.critic.load_weights(str(critic_path))
                self.logger.info(f"Loaded Critic from {critic_path}")
            except Exception as e:
                self.logger.error(f"Failed to load Critic: {e}")
                success = False
        else:
            self.logger.warning(f"No Critic weights found at {critic_path}")
            success = False

        return success

    def hot_swap_model(self, new_model_name: str, new_model_base_path: Path) -> bool:
        """
        Updates the internal state to point to a new model directory and loads weights.
        Used by the API to switch the active scheduler on the fly.
        """
        self.logger.info(
            f"Initiating Hot-Swap to model: '{new_model_name}' at {new_model_base_path}"
        )

        if not new_model_base_path.exists():
            self.logger.error(
                f"Hot-Swap failed: Directory {new_model_base_path} does not exist."
            )
            return False

        # Attempt load
        if self.load_models(specific_dir=new_model_base_path):
            # If load succeeds, update internal state
            self.model_base_dir = new_model_base_path
            self.current_model_name = new_model_name

            # Update TensorBoard writer to new location so logs don't mix
            self.log_dir = self.model_base_dir / "logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.summary_writer = tf.summary.create_file_writer(str(self.log_dir))

            self.logger.info(
                f"Hot-Swap successful. Active model is now '{new_model_name}'"
            )
            return True
        else:
            self.logger.error(
                "Hot-Swap failed during weight loading. Reverting to previous state."
            )
            return False

    # def load_models(
    #     self,
    #     actor_weights_path: Optional[Path] = None,
    #     critic_weights_path: Optional[Path] = None,
    # ) -> None:
    #     actor_path = (
    #         actor_weights_path if actor_weights_path else self.get_actor_save_path()
    #     )
    #     critic_path = (
    #         critic_weights_path if critic_weights_path else self.get_critic_save_path()
    #     )

    #     dummy_input = np.zeros((1, self.input_dim), dtype=np.float32)
    #     if not self.actor.built:
    #         self.actor(dummy_input)
    #     if not self.critic.built:
    #         self.critic(dummy_input)

    #     if actor_path.exists() and actor_path.is_file():
    #         try:
    #             self.actor.load_weights(str(actor_path))
    #             self.logger.info(f"Actor model weights loaded from {actor_path}")
    #         except Exception as e:
    #             self.logger.warning(
    #                 f"Could not load Actor weights from {actor_path}: {e}. Using initial weights."
    #             )
    #     else:
    #         self.logger.warning(
    #             f"No Actor model weights found at {actor_path}. Using initial weights."
    #         )

    #     if critic_path.exists() and critic_path.is_file():
    #         try:
    #             self.critic.load_weights(str(critic_path))
    #             self.logger.info(f"Critic model weights loaded from {critic_path}")
    #         except Exception as e:
    #             self.logger.warning(
    #                 f"Could not load Critic weights from {critic_path}: {e}. Using initial weights."
    #             )
    #     else:
    #         self.logger.warning(
    #             f"No Critic model weights found at {critic_path}. Using initial weights."
    #         )

    def _get_state_vector(
        self, schedule_request: ScheduleRequest
    ) -> Optional[np.ndarray]:
        try:
            jobs_df, nodes_df, latency_matrix = self.data_transformer.transform(
                schedule_request
            )
            state_vector = self.feature_engineer.build_features(
                jobs_df, nodes_df, latency_matrix
            )
            return state_vector
        except ValueError as ve:
            self.logger.error(f"Error generating state vector: {ve}")
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error in _get_state_vector: {e}")
            return None

    # def calculate_reward(self, runtime_ms: float, throughput: float) -> float:
    #     runtime_s = runtime_ms / 1000.0
    #     reward = throughput * 1.0
    #     if runtime_s > 0.001:
    #         reward -= runtime_s * 0.1
    #     elif runtime_s <= 0.001 and throughput > 0:
    #         reward += 0.5
    #     return float(reward)

    def calculate_reward(self, runtime_ms: float, throughput: float) -> float:
        """
        Calculates a reward score based on throughput (benefit) and runtime (cost).
        """
        THROUGHPUT_WEIGHT: float = 1.0
        RUNTIME_PENALTY_WEIGHT: float = 10.0
        # Handle cases where the strategy failed or returned an invalid time
        if runtime_ms < 0:
            self.logger.warning(
                f"Invalid runtime ({runtime_ms}ms). Returning -inf reward."
            )
            return -float("inf")

        # Convert runtime from milliseconds to seconds
        runtime_s = runtime_ms / 1000.0

        # Calculate the two components
        throughput_benefit = throughput * THROUGHPUT_WEIGHT
        runtime_cost = runtime_s * RUNTIME_PENALTY_WEIGHT

        # Final reward is benefit minus cost
        reward = throughput_benefit - runtime_cost

        self.logger.debug(
            f"Reward calc: (T={throughput} * {THROUGHPUT_WEIGHT}) - (R_s={runtime_s:.4f} * {RUNTIME_PENALTY_WEIGHT}) = {reward:.3f}"
        )
        return float(reward)

    def predict_strategy_index(
        self, state_vector: np.ndarray, deterministic: bool = True
    ) -> int:
        if (
            state_vector is None
            or state_vector.ndim == 0
            or state_vector.shape[0] != self.input_dim
        ):
            self.logger.error(
                f"Invalid state_vector for prediction. Expected dim {self.input_dim}, got {state_vector.shape if state_vector is not None else 'None'}"
            )
            return 0

        full_probabilities = self.actor.predict(
            np.expand_dims(state_vector, axis=0), verbose=0
        )[0]
        actual_probabilities = full_probabilities[: self.output_dim]

        if self.output_dim > 1:
            prob_sum = np.sum(actual_probabilities)
            if prob_sum > 1e-6:
                actual_probabilities = actual_probabilities / prob_sum
            else:
                actual_probabilities = np.ones(self.output_dim) / self.output_dim

        if deterministic:
            predicted_strategy_idx = np.argmax(actual_probabilities)
        else:
            predicted_strategy_idx = np.random.choice(
                self.output_dim, p=actual_probabilities
            )

        self.logger.info(
            f"AI Model Action Probs (first {self.output_dim}): {actual_probabilities.round(3)}, Chosen Idx: {predicted_strategy_idx}"
        )
        return int(predicted_strategy_idx)

    def predict_best_strategy_name(
        self, schedule_request: ScheduleRequest, deterministic: bool = True
    ) -> Optional[str]:
        state_vector = self._get_state_vector(schedule_request)
        if state_vector is None:
            self.logger.warning(
                "Could not generate state vector. Falling back to default strategy."
            )
            return self.strategy_names[0] if self.strategy_names else None

        predicted_idx = self.predict_strategy_index(
            state_vector, deterministic=deterministic
        )

        if 0 <= predicted_idx < len(self.strategy_names):
            return self.strategy_names[predicted_idx]
        else:
            self.logger.error(
                f"Predicted strategy index {predicted_idx} is out of bounds for strategy_names (len {len(self.strategy_names)}). Falling back."
            )
            return self.strategy_names[0] if self.strategy_names else None

    def collect_experience(
        self,
        schedule_request: ScheduleRequest,
        chosen_strategy_name: str,
        runtime_ms: float,
        throughput: float,
    ) -> None:
        state_vector = self._get_state_vector(schedule_request)
        if state_vector is None:
            self.logger.error(
                "Cannot collect experience: failed to generate state vector."
            )
            return

        try:
            action_index = self.strategy_names.index(chosen_strategy_name)
        except ValueError:
            self.logger.error(
                f"Cannot collect experience: Strategy name '{chosen_strategy_name}' not in {self.strategy_names}."
            )
            return

        reward = self.calculate_reward(runtime_ms, throughput)
        next_state_vector: Optional[np.ndarray] = None
        done: bool = True

        self.replay_buffer.add(
            state_vector, action_index, reward, next_state_vector, done
        )
        self.logger.info(
            f"Experience collected: Strategy '{chosen_strategy_name}' (idx {action_index}), Reward {reward:.2f}, Done: {done}"
        )

    def _compute_advantages_gae(
        self,
        rewards_np: np.ndarray,
        values_np: np.ndarray,
        next_values_np: np.ndarray,
        dones_np: np.ndarray,
    ) -> np.ndarray:
        advantages = np.zeros_like(rewards_np)
        last_gae_lam = 0.0
        for t in reversed(range(len(rewards_np))):
            if dones_np[t]:
                delta = rewards_np[t] - values_np[t]
                last_gae_lam = delta
            else:
                delta = rewards_np[t] + self.gamma * next_values_np[t] - values_np[t]
                last_gae_lam = delta + self.gamma * self.gae_lambda * last_gae_lam
            advantages[t] = last_gae_lam
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)
        return advantages

    @tf.function
    def _train_step_tf(
        self,
        states: tf.Tensor,
        actions: tf.Tensor,
        advantages: tf.Tensor,
        old_action_log_probs_taken: tf.Tensor,
        target_values: tf.Tensor,
    ) -> tuple[tf.Tensor, tf.Tensor, tf.Tensor]:
        with tf.GradientTape() as actor_tape, tf.GradientTape() as critic_tape:
            current_action_probs_all = self.actor(states)
            action_indices_for_gather = tf.stack(
                [tf.range(tf.shape(actions)[0], dtype=tf.int32), actions], axis=1
            )
            current_action_log_probs_taken = tf.math.log(
                tf.gather_nd(current_action_probs_all, action_indices_for_gather)
                + 1e-10
            )
            ratios = tf.exp(current_action_log_probs_taken - old_action_log_probs_taken)
            surr1 = ratios * advantages
            surr2 = (
                tf.clip_by_value(ratios, 1.0 - self.policy_clip, 1.0 + self.policy_clip)
                * advantages
            )
            actor_loss = -tf.reduce_mean(tf.minimum(surr1, surr2))
            entropy = -tf.reduce_sum(
                current_action_probs_all
                * tf.math.log(current_action_probs_all + 1e-10),
                axis=1,
            )
            actor_loss -= self.entropy_coefficient * tf.reduce_mean(entropy)
            current_state_values = self.critic(states)
            critic_loss = tf.reduce_mean(
                tf.square(target_values - tf.squeeze(current_state_values))
            )

        actor_gradients = actor_tape.gradient(
            actor_loss, self.actor.trainable_variables
        )
        critic_gradients = critic_tape.gradient(
            critic_loss, self.critic.trainable_variables
        )
        self.actor_optimizer.apply_gradients(
            zip(actor_gradients, self.actor.trainable_variables)
        )
        self.critic_optimizer.apply_gradients(
            zip(critic_gradients, self.critic.trainable_variables)
        )
        return actor_loss, critic_loss, tf.reduce_mean(entropy)

    def train_agent(self) -> None:
        if len(self.replay_buffer) < self.ppo_batch_size:
            self.logger.info(
                f"Not enough samples in replay buffer ({len(self.replay_buffer)}) to train. Need at least {self.ppo_batch_size}."
            )
            return

        self.logger.info(
            f"Starting PPO agent training cycle: {self.epochs_per_update} epochs, PPO batch size {self.ppo_batch_size}."
        )
        num_samples_for_cycle = min(len(self.replay_buffer), self.ppo_batch_size * 10)
        if num_samples_for_cycle < self.ppo_batch_size:
            self.logger.warning(
                f"Training aborted: Not enough samples ({num_samples_for_cycle}) for even one PPO batch."
            )
            return

        states_np, actions_np, rewards_np, next_states_np, dones_np = (
            self.replay_buffer.sample(num_samples_for_cycle)
        )
        if states_np is None:
            self.logger.warning(
                "Training aborted: No samples returned from replay buffer for this cycle."
            )
            return

        values_np = tf.squeeze(
            self.critic.predict(states_np, batch_size=self.ppo_batch_size, verbose=0)
        ).numpy()
        next_values_np = tf.squeeze(
            self.critic.predict(
                next_states_np, batch_size=self.ppo_batch_size, verbose=0
            )
        ).numpy()
        old_action_probs_all_np = self.actor.predict(
            states_np, batch_size=self.ppo_batch_size, verbose=0
        )
        action_indices_np = np.stack(
            [np.arange(actions_np.shape[0]), actions_np], axis=1
        )
        old_action_probs_taken_np = tf.gather_nd(
            old_action_probs_all_np, action_indices_np
        ).numpy()
        old_action_log_probs_taken_np = np.log(old_action_probs_taken_np + 1e-10)
        advantages_np = self._compute_advantages_gae(
            rewards_np, values_np, next_values_np, dones_np
        )
        target_values_np = advantages_np + values_np

        dataset = (
            tf.data.Dataset.from_tensor_slices(
                (
                    states_np,
                    actions_np,
                    advantages_np,
                    old_action_log_probs_taken_np,
                    target_values_np,
                )
            )
            .shuffle(buffer_size=num_samples_for_cycle)
            .batch(self.ppo_batch_size, drop_remainder=True)
        )

        for epoch in range(self.epochs_per_update):
            epoch_actor_loss, epoch_critic_loss, epoch_entropy = 0, 0, 0
            num_batches_processed = 0
            for s_batch, a_batch, adv_batch, old_log_p_batch, tv_batch in dataset:
                actor_loss, critic_loss, entropy = self._train_step_tf(
                    s_batch, a_batch, adv_batch, old_log_p_batch, tv_batch
                )
                epoch_actor_loss += actor_loss.numpy()
                epoch_critic_loss += critic_loss.numpy()
                epoch_entropy += entropy.numpy()
                num_batches_processed += 1

            if num_batches_processed > 0:
                avg_actor = epoch_actor_loss / num_batches_processed
                avg_critic = epoch_critic_loss / num_batches_processed
                avg_entropy = epoch_entropy / num_batches_processed

                self.logger.info(
                    f"PPO Epoch {epoch+1}/{self.epochs_per_update} - "
                    f"Avg Actor Loss: {avg_actor:.4f}, "
                    f"Avg Critic Loss: {avg_critic:.4f}, "
                    f"Avg Entropy: {avg_entropy:.4f}"
                )
                with self.summary_writer.as_default():
                    tf.summary.scalar(
                        "Loss/Actor", avg_actor, step=self.global_train_step
                    )
                    tf.summary.scalar(
                        "Loss/Critic", avg_critic, step=self.global_train_step
                    )
                    tf.summary.scalar(
                        "Policy/Entropy", avg_entropy, step=self.global_train_step
                    )
                    self.summary_writer.flush()

                # increment step after every epoch so we see the curve
                # evolving within the cycle
                self.global_train_step += 1

                # self.logger.info(
                #     f"PPO Epoch {epoch+1}/{self.epochs_per_update} - "
                #     f"Avg Actor Loss: {epoch_actor_loss/num_batches_processed:.4f}, "
                #     f"Avg Critic Loss: {epoch_critic_loss/num_batches_processed:.4f}, "
                #     f"Avg Entropy: {epoch_entropy/num_batches_processed:.4f}"
                # )
            else:
                self.logger.warning(
                    f"PPO Epoch {epoch+1}/{self.epochs_per_update} - No batches processed."
                )
                break

        self.logger.info("PPO agent training cycle finished.")
