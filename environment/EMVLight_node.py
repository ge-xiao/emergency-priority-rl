import numpy as np
import pandas as pd
import subprocess
from sumolib import checkBinary
import time
import traci
import json
import os

class Node:
    def __init__(self, name,mode,phases,sim,neighbor,tot_neighbor):

        self.name = name
        self.mode=mode
        self.prev_action=-1
        self.phases=phases
        self.ilds_in=[]
        self.sim=sim
        self.neighbor=neighbor
        self.tot_neighbor=tot_neighbor
        self.n_a=len(phases)
        self.n_judge_a= 2 ** len(tot_neighbor)


        self.ev_waitTimes = dict()
        self.last_action_EVs = []
        self.cur_action_EVs = []


        self.comingInfo = {}


        self.num_fingerprint = self.n_a-1
        self.fingerprint = [0 for i in range(self.num_fingerprint)]  # local policy


        self.vehicle_size_min_gap = 7.5
        self.norm_speed=10
        self.norm_wait=50


        lanes_in = self.sim.trafficlight.getControlledLanes(name)
        self.lanes_in=lanes_in
        # controlled edges: e:j,i
        # lane ilds: ild:j,i_k for road ji, lane k.
        edges_in = []
        ilds_in = []
        for lane_name in lanes_in:
            ild_name = lane_name
            if ild_name not in ilds_in:
                ilds_in.append(ild_name)
        for ilds in ilds_in:
            edge=self.sim.lane.getEdgeID(ilds)
            if edge not in edges_in:
                edges_in.append(edge)
        self.edges_in=edges_in
        #print(self.name)
        #print((self.edges_in))
        # nodes[node_name].edges_in = edges_in
        self.ilds_in = ilds_in
        self.last_lane_hasev=[0 for lane in self.ilds_in]
        self.cur_lane_hasev=[0 for lane in self.ilds_in]


        self.lanes_length = {lane: self.sim.lane.getLength(lane) for lane in self.ilds_in}

        for neighbor in self.tot_neighbor:
            f_e = self.name + '-' + neighbor
            f_l_n = self.sim.edge.getLaneNumber(f_e)
            for f_i in range(f_l_n):
                f_lane = f_e + "_" + str(f_i)
                if f_lane not in self.lanes_length:
                    self.lanes_length[f_lane]=self.sim.lane.getLength(f_lane)


        self.lanearea_length = {lane: self.sim.lanearea.getLength(lane) for lane in self.ilds_in}
        self.lane_meanWait=[0 for lane in self.ilds_in]


        #当前在场的ev
        self.tot_ev=set()

        self.hasJudgedEV={}
        self.hasJudgedEV_route = {}
        self.notJudgedEV=[]
        self.hasSendEV=[]
        self.tot_judge_reward={}
        self.ev_cover={}
        self.ev_waste={}
        self.IDs_mp={lane: [] for lane in self.ilds_in}

        #信号灯控制的n_s，由env初始化
        self.n_s = -1
        # 判断特车的状态,直接计算好像不好
        self.judge_n_s=len(self.ilds_in)+3+len(self.neighbor)

        #存放是否为哪种类型的agent
        self.is_p=False
        self.is_s=False
        self.from_n=None
        self.next=None


    def get_node_state(self):

        inlanes=[min(1, self.sim.lane.getLastStepVehicleNumber(lane) / (self.lanes_length[lane] / self.vehicle_size_min_gap)) for lane in self.ilds_in]
        outlanes=[]

        for neighbor in self.neighbor:
            f_e = self.name + '-' + neighbor
            f_l_n = self.sim.edge.getLaneNumber(f_e)
            for f_i in range(f_l_n):
                f_lane = f_e + "_" + str(f_i)
                outlanes.append(min(1, self.sim.lane.getLastStepVehicleNumber(f_lane) / (self.lanes_length[f_lane] / self.vehicle_size_min_gap)))

        d_ev=self.compute_multi_emergency_obs()

        return inlanes,outlanes,d_ev



    def compute_multi_emergency_obs(self):
        #需要初始化is_p
        self.is_p=False
        self.is_s=False

        lanes = self.ilds_in
        d_ev=[-1 for edge in self.edges_in]

        for f_e in self.edges_in:
            idx=0
            f_l_n = self.sim.edge.getLaneNumber(f_e)
            for f_i in range(f_l_n):
                f_lane = f_e + "_" + str(f_i)
                #outlanes.append(min(1, self.sim.lane.getLastStepVehicleNumber(f_lane) / (self.lanes_length[f_lane] / self.vehicle_size_min_gap)))
                IDs = self.sim.lane.getLastStepVehicleIDs(f_lane)
                self.IDs_mp[f_lane]=IDs

                for i in range(len(IDs)):
                    vc = IDs[i]

                    if vc.find("emergency") != -1:

                        if self.sim.vehicle.getLaneID(vc).find(":")!=-1:
                            continue

                        self.is_p=True

                        route = self.sim.vehicle.getRoute(vc)

                        f_idx=0
                        for j in range(len(route)):
                            if route[j]==f_e:
                                f_idx=j
                                break

                        if f_idx==len(route)-1:
                            continue


                        self.next=route[f_idx+1].split('-')[1]
                        # print(self.is_p)
                        # print(vc)
                        # print(self.next)

                        #speed = self.sim.vehicle.getSpeed(vc)

                        pos = self.sim.vehicle.getLanePosition(vc)
                        length = self.lanes_length[f_lane]
                        toCenter = int(length - pos)
                        d_ev[idx]=(float)(toCenter/100)

            idx+=1


        return d_ev



    def getPresure(self):

        links = self.sim.trafficlight.getControlledLinks(self.name)

        #得到lane的连接
        links_map = {}
        for link in links:
            if link[0][0] not in links_map:
                # 变成一个列表
                links_map[link[0][0]] = [link[0][1]]
            else:
                links_map[link[0][0]].append(link[0][1])

        lanes = self.ilds_in
        presure=0
        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            t1=min(1, self.sim.lane.getLastStepVehicleNumber(lane) / (self.lanes_length[lane] / self.vehicle_size_min_gap))

            for to_lane in links_map[lane]:
                to_edge=self.sim.lane.getEdgeID(to_lane)
                hm = self.sim.edge.getLaneNumber(to_edge)
                t2=min(1, self.sim.lane.getLastStepVehicleNumber(to_lane) / (self.lanes_length[to_lane] / self.vehicle_size_min_gap))
                t1=t1-t2/hm

            presure+=abs(t1)
        return presure




    def getReward(self):

        reward = 0

        if self.is_p==True:
            reward=-1
        else:
            presure=self.getPresure()
            if self.is_s==True:
                t2=0

                f_e = self.from_n + '-' + self.name
                f_l_n = self.sim.edge.getLaneNumber(f_e)
                for f_i in range(f_l_n):
                    f_lane = f_e + "_" + str(f_i)
                    t2+=min(1, self.sim.lane.getLastStepVehicleNumber(f_lane) / (self.lanes_length[f_lane] / self.vehicle_size_min_gap))
                reward=-0.5*presure-0.5*t2/f_l_n

            else:
                reward=-1*presure

        return reward


    def getPhase(self,action):
        return self.phases[action]

    def time_to_act(self):
        if len(self.notJudgedEV)>0:
            return True

    def testTime(self):
        lanes = self.ilds_in

        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            IDs=self.sim.inductionloop.getLastStepVehicleIDs(lane)
            if self.name=='t_1_5':
                print(IDs)
                for ID in IDs:
                    if "emergency" in ID :
                        print(ID)


