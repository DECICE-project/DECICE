# AI Scheduler Training Workflow

This document outlines the steps and scripts involved in generating training data, preparing features, and training the AI Scheduler model.

## Training Loop Steps

**Step 1: Generate Synthetic Training Scenario Data**

* **Script:** `src/scripts/generate_synthetic_data.py`
* **Example Command (run from `src/` or project root):**
    ```bash
    ENVIRONMENT="local" python -m scripts.generate_synthetic_data --num_files 100 --jobs_max 30 --nodes_max 15 --output_dir data/scenarios/training
    ```
    This command will generate 100 scenario files in the specified output directory. Adjust parameters as needed. The default output directory is defined in `core.config.settings.SCENARIO_DIR_TRAIN`.

**Step 2: Generate Synthetic Testing Scenario Data**
* **Script:** `src/scripts/generate_synthetic_data.py`
* **Example Command (run from `src/` or project root):**
    ```bash
    ENVIRONMENT="local" python -m scripts.generate_synthetic_data --num_files 100 --jobs_max 30 --nodes_max 15 --output_dir data/scenarios/testing
    ```

**Step 2: Populate Initial Replay Buffer (with Unscaled Features) & Analyze Feature Ranges**

This step is typically done **once initially** or when you significantly change your feature engineering or scenario generation, to understand the raw feature distributions.

* **A. Populate Buffer with Unscaled Features:**
    * To process the generated scenario files, run all scheduling strategies for each, and collect `(state, action, reward)` experiences. At this stage, the `state_vector`s will be *unscaled* because feature scalers haven't been created yet.
    * **Script:** `src/scripts/populate_replay_buffer.py`
    * **Example Command:**
        ```bash
        ENVIRONMENT="local" python -m scripts.populate_replay_buffer --scenario_dir data/scenarios/training --replay_buffer_output data/replay_buffers/replay_buffer_UNSCALED.pkl
        ```
        *Ensure `FeatureEngineer` in `core/data_processing.py` is set to output raw features if the scaler file (e.g., `models/scalers/all_feature_scalers.joblib`) doesn't exist (which it won't on the first run).*

* **B. Analyze Feature Ranges:**
    * To understand the statistical properties (min, max, mean, std) of the *unscaled* features generated in the previous step. This information is crucial for fitting the feature scalers.
    * **Script:** `src/scripts/analyze_feature_ranges.py`
    * **Example Command:**
        ```bash
         ENVIRONMENT="local" python -m scripts.analyze_feature_ranges --replay_buffer_path data/replay_buffers/replay_buffer_UNSCALED.pkl
        ```
    * Examine the console output to understand the range of each feature.

**Step 3: Fit and Save Feature Scalers**

* Based on the statistics of the unscaled features (from Step **2B**), this script fits a scaler (e.g., `MinMaxScaler`) for each feature and saves these *fitted* scalers to disk.
* **Script:** `src/scripts/fit_and_save_scalers.py`
* **Example Command:**
    ```bash
    ENVIRONMENT="local" python -m scripts.fit_and_save_scalers \
    --replay_buffer_path data/replay_buffers/replay_buffer_UNSCALED.pkl \
    --scalers_output_path models/scalers
    ```
    This will create files like `models/scalers/all_feature_scalers.joblib`.

**Step 4: Re-populate Replay Buffer with SCALED Features**

* Now that the scalers are created and saved, re-run the replay buffer population. This time, `FeatureEngineer` (used by `AIScheduler`) will load the fitted scalers and ensure all `state_vector`s stored in the replay buffer are **scaled**. This is the buffer you will use for actual training.
* **Script:** `src/scripts/populate_replay_buffer.py`
* **Example Command:**
    ```bash
    ENVIRONMENT="local" python -m scripts.populate_replay_buffer --scenario_dir data/scenarios/training --replay_buffer_output data/replay_buffers/replay_buffer_SCALED.pkl
    ```
    *Verify from the logs that `FeatureEngineer` successfully loads the scalers.*

**Step 5: Train the AI Scheduler Model**

* Train the PPO agent (Actor and Critic networks) using the experiences stored in the **scaled** replay buffer.
* **Script:** `src/scripts/train_ai_scheduler.py`
* **Example Command (starting fresh or from a checkpoint):**
    ```bash
    ENVIRONMENT="local" python -m scripts.train_ai_scheduler --replay_buffer_path data/replay_buffers/replay_buffer_SCALED.pkl --num_training_cycles 500
    ```
    * Monitor training logs (Actor/Critic loss, Entropy).
    * Model weights will be saved periodically to the directory specified by `settings.MODELS_BASE_DIR` (e.g., `models/`).

**Step 6: Evaluate Trained Models**

* Evaluate the performance of saved model checkpoints on a separate, unseen set of test scenarios.
* **Script:** `src/scripts/evaluate_ai_scheduler.py`
* **Prerequisite:** Have test scenarios in a directory (e.g., `data/scenarios/test/`, configured via `settings.SCENARIO_DIR_TEST`).
* **Example Command:**
    ```bash
    ENVIRONMENT="local" python -m scripts.evaluate_ai_scheduler \
    --test_scenario_dir data/scenarios/testing/ \
    --actor_weights models/ai_scheduler_actor_weights.weights.h5 \
    --critic_weights models/ai_scheduler_critic_weights.weights.h5 \
    --scalers_path models/scalers/all_feature_scalers.joblib
    ```
    *(Adjust paths to specific checkpoint weights if needed).*
    * Collect Average Reward, Throughput, and strategy selection counts.
