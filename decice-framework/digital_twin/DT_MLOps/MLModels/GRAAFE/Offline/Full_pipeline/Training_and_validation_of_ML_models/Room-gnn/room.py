import ast
import logging
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd

from utils import *


class Marconi100Room:
  """
  Class representing the Marconi 100 (M100) room and its nodes distribution.

  Upon initialization, the class creates the `self.room_grid` member. It
  represents a 3D spatial grid of nodes, with each entry being the integer ID
  for one node. -1 is not a node, but rather a placeholder for an empty slot in
  the room.
  See also https://gitlab.com/ecs-lab/exadata/-/blob/main/documentation/racks_spatial_distribution.md
  The above layout is the default one, but a different layout can be provided
  via the `racks_layout` argument.
  """
  def __init__(self, racks_layout: np.ndarray | None = None):
    self.logger = logging.getLogger(__name__)

    # Room information and specifics
    self.nodes_per_rack = 20
    self.rack_height = 2.0  # IBM 7965-S42: 2020 mm tall with top rack extension,
                       # 1899 mm without; approximated to 2 meters
    if racks_layout is None:
      racks_layout = np.array([
                       [48,47,46,45,-1,44,43,42,41,40,39,38,37,36,35,34,33,-1],
                       [32,31,30,29,-1,28,27,26,25,-1,24,23,22,21,20,19,18,-1],
                       [17,16,15,14,13,12,11,10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
                     )
    # Distances between neighbors in x, y, z directions
    # NOTE: x and y array axes are SWAPPED with respect to the spatial axes!!!
    self.neigh_distances = [4.0, 1.0, self.rack_height/(self.nodes_per_rack-1)]

    # Initialize array representation of room
    self.room_grid = np.zeros((*(racks_layout.shape), self.nodes_per_rack),
                              dtype=int)

    for h in range(self.nodes_per_rack):
      slice_h = self.nodes_per_rack*racks_layout + h
      slice_h[slice_h < 0] = -1
      self.room_grid[:, :, h] = slice_h


    # Convenience members: number of nodes and list of node IDs in string form
    self.total_nodes = self.nodes_per_rack * (racks_layout != -1).sum()
    self.nodes_list = [str(_) for _ in np.unique(self.room_grid)]
    self.nodes_list.remove("-1")

  def get_neighbors_and_distances(self, node: int) -> dict[int: float]:
    """
    Return direct neighbors of `node` and their distances from it

    Keys of returned dict are neighbor nodes IDs, while values are their
    distances in meters from `node`
    """
    if str(node) not in self.nodes_list:
      raise ValueError(f"{node} is not a valid node number")
    # Get coordinates of node in room array
    node_pos = np.ravel(np.where(self.room_grid == node))

    self.logger.debug(f"Neighbors of room[{node_pos}] = "
                      f"{self.room_grid[node_pos[0]][node_pos[1]][node_pos[2]]}:")


    distances = {}
    
    # Move forward and backward by 1
    for shift in (-1,1):
      # Move along the 3 spatial axes
      for dim in range(3):
        mov = np.zeros(3, dtype = int)
        mov[dim] = shift
        # Position of neighbor, if any
        pos = node_pos+mov
        if (pos[dim] not in (-1, self.room_grid.shape[dim])  # not OOB
            and self.room_grid[pos[0]][pos[1]][pos[2]] != -1):                 # not empty slot
          value = self.room_grid[pos[0]][pos[1]][pos[2]]
          dist = self.neigh_distances[dim]
          self.logger.debug(f"room[{pos}] = {value}, dist = {dist}")
          distances[value] = dist
    return distances

  def get_edge_tuples_and_weights(self) -> tuple[np.ndarray, np.ndarray]:
    """
    Get matrices of vertex-vertex edge tuples and weights of the room graph

    That is, the function returns a n_edges-by-2 matrix, with each row having
    the source and the target nodes of a single edge, and a n_edges-long
    vector, containing the edges weights, which are *inversely proportional* to
    the distance between both nodes. The first matrix is the transpose of the
    COO format required by PyTorch.
    """
    tuples_list = []
    weights = []
    # Iterate over arr elements
    iterator = np.nditer(self.room_grid, flags=['multi_index'])
    for it in iterator:
      src = it.item()  # element value
      if src == -1:  # empty slot
        continue
      # Loop over neighbors of the current element
      for trg, dist in self.get_neighbors_and_distances(src).items():
        tuples_list.append((src, trg))
        weights.append(1.0 / dist)

    return np.array(tuples_list, dtype=int), np.array(weights, dtype=float)

  def _decorate_3d_plot(self, ax: Axes) -> Axes:
    """Add axis labels and other utilities to `ax`, return updated version"""
    ## X-axis
    ax.set_yticks(np.arange(0.5, 18.5, 1))
    ax.set_yticklabels(list(range(4, 22)))
    ax.set_ylabel("X")
    ## Y-axis
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels([10, 6, 2])
    ax.set_xlabel("Y")
    ## Z-axis
    ax.set_zticks(np.arange(0.5, 21.5, 1))
    ax.set_zticklabels(np.arange(0.05, 2.15, 0.1).round(2))
    ax.set_zlabel("Z")
    return ax

  def visualize_nodes(self, nodes: list[int]) -> None:
    """Visualize given list of nodes in a 3D plot"""
    empty_room = (self.room_grid >= 0)
    nodes_tiles = np.logical_or.reduce([self.room_grid == i for i in nodes])

    ax = plt.figure(figsize=(9, 9)).add_subplot(projection='3d')
    ax.voxels(empty_room, facecolors='#FFD65DC0')
    ax.voxels(nodes_tiles, facecolors='blue')

    # Decorate plot
    ax = self._decorate_3d_plot(ax)
    ax.set_title(f"Position of nodes {nodes}")

    plt.show()

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)

  M100 = Marconi100Room(None)
  M100.visualize_nodes([0])
  edges, weights = M100.get_edge_tuples_and_weights()
  np.savetxt('edges.csv', edges, fmt='%d')
  np.savetxt('weights.csv', weights, fmt='%.2f')