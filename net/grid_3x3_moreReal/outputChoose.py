
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
        self.edges[v][u] = weight

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



class Dynamic_route():
    def __init__(self):
        self.seed=12
        self.port=8000
        self._init_sim(True)

        nodes = {}
        for node_name in self.sim.trafficlight.getIDList():
            # print(node_name)
            nodes[node_name] = 1
        self.sorted_nodes = sorted(list(nodes.keys()))

        self.name_idx={}
        for i in range(len(self.sorted_nodes)):
            self.name_idx[self.sorted_nodes[i]]=i

        self.tot_ilds_in = {}
        for node in self.sorted_nodes:
            lanes_in = self.sim.trafficlight.getControlledLanes(node)
            ilds_in = []
            for lane_name in lanes_in:
                ild_name = lane_name
                if ild_name not in ilds_in:
                    ilds_in.append(ild_name)
            self.tot_ilds_in[node] = ilds_in


        with open('./trafficInfo.json', encoding='utf-8') as a:
            trafficInfo = json.load(a)
        self.neighbor_map=trafficInfo["neighbor_map"]
        self.tot_neighbor_map=trafficInfo['tot_neighbor_map']




    def _init_sim(self, gui=False):

        sumocfg_file = 'exp.sumocfg'
        if gui:
            app = 'sumo-gui'
        else:
            app = 'sumo'
        #app = 'sumo-gui'

        command = [checkBinary(app), '-c', sumocfg_file]
        command += ['--seed', str(self.seed)]
        command += ['--remote-port', str(self.port)]
        command += ['--no-step-log', 'True']

        command += ['--time-to-teleport', '300']
        command += ['--no-warnings', 'True']
        command += ['--duration-log.disable', 'True']

        if app == 'sumo-gui':
            #sumo_cmd.extend(['--start', '--quit-on-end'])
            command+=[ '--quit-on-end']

        subprocess.Popen(command)

        # wait 2s to establish the traci server
        time.sleep(0.2)
        self.sim = traci.connect(port=self.port)

    def output(self):
        info = {}

        tot_chs = {}
        for node_name in self.sorted_nodes:
            print(node_name)
            chs=[[]]
            tot_neighbors=self.tot_neighbor_map[node_name]
            for nnode_name in tot_neighbors:
                f_e=node_name+'-'+nnode_name
                f_l_n = self.sim.edge.getLaneNumber(f_e)
                tp=chs.copy()
                chs=[]
                for ch in tp:
                    ch_c=ch.copy()
                    chs.append(ch_c)

                    for f_i in range(f_l_n):
                        ch_c = ch.copy()
                        f_lane = f_e + "_" + str(f_i)
                        ch_c.append(f_lane)
                        chs.append(ch_c)
                print(chs)
            print(chs)
            print(len(chs))
            tot_chs[node_name]=chs
        info["tot_chs"]=tot_chs
        with open('tot_chs.json', 'w', encoding='utf-8') as b:
            # ensure_ascii 显示中文，不以ASCII的方式显示
            json.dump(info, b, ensure_ascii=False, indent=2)  # indent 缩进



    def run(self):
        """execute the TraCI control loop"""
        step = 0
        while step<3600:
            self.sim.simulationStep()
            step += 1
            self.output()




if __name__ == "__main__":

    dynamic_route=Dynamic_route()
    dynamic_route.run()