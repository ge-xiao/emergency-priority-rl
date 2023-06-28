from multiprocessing.connection import wait
import os
import sys
import optparse
import random
import json
import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os

from queue import PriorityQueue

class Graph:
    def __init__(self, num_of_vertices):
        self.vertices = num_of_vertices
        #距离表
        self.edges = [[-1 for i in range(num_of_vertices)] for j in range(num_of_vertices)]
        #记录被访问过的节点
        self.visited = []

    def add_edge(self, u, v, weight):
        self.edges[u][v] = weight
        #self.edges[v][u] = weight

    def dijkstra(self, start_vertex):
        #开始时定义源节点到其他所有节点的距离为无穷大
        D = {v: float('inf') for v in range(self.vertices)}
        #源节点到自己的距离为0
        D[start_vertex] = 0
        #优先队列
        pq = PriorityQueue()
        pq.put((0, start_vertex))
        # 记录每个节点的前节点，便于回溯
        previousVertex = {}

        while not pq.empty():
            #得到优先级最高的节点，也就是前节点到其他节点距离最短的节点作为当前出发节点
            (dist, current_vertex) = pq.get()
            #标记已访问过的节点(最有路径集合)
            self.visited.append(current_vertex)

            for neighbor in range(self.vertices):
                #邻居节点之间距离不能为-1
                if self.edges[current_vertex][neighbor] != -1:
                    distance = self.edges[current_vertex][neighbor]
                    #已经访问过的节点不能再次被访问
                    if neighbor not in self.visited:
                        #更新源节点到其他节点的最短路径
                        old_cost = D[neighbor]
                        new_cost = D[current_vertex] + distance
                        if new_cost < old_cost:
                            #加入优先队列
                            pq.put((new_cost, neighbor))
                            D[neighbor] = new_cost
                            previousVertex[neighbor] = current_vertex
        return D, previousVertex

    def path(self,start_v,to_v,previousVertex):
        path = []
        key = to_v
        # 回溯，得到源节点到目标节点的最佳路径

        while True:
            if key == start_v:
                path.append(start_v)
                break
            else:
                path.append(key)
                key = previousVertex[key]
        real_path = []
        for point in path[:: -1]:
            real_path.append(point)
        return real_path