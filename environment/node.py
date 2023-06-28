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
        # edges_in = []
        ilds_in = []
        for lane_name in lanes_in:
            ild_name = lane_name
            if ild_name not in ilds_in:
                ilds_in.append(ild_name)
        # nodes[node_name].edges_in = edges_in
        self.ilds_in = ilds_in
        self.last_lane_hasev=[0 for lane in self.ilds_in]
        self.cur_lane_hasev=[0 for lane in self.ilds_in]
        self.lanes_length = {lane: self.sim.lane.getLength(lane) for lane in self.ilds_in}

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


    def get_node_state(self):

        # for ild in node.ilds_in:
        phase_id = [1 if self.prev_action == i else 0 for i in range(len(self.phases))]  # one-hot encoding

        density=[min(1, self.sim.lanearea.getLastStepVehicleNumber(lane) / (self.lanearea_length[lane] / self.vehicle_size_min_gap)) for lane in self.ilds_in]


        queue=[min(1, self.sim.lanearea.getLastStepHaltingNumber(lane) / (self.lanearea_length[lane] / self.vehicle_size_min_gap)) for lane in self.ilds_in]

        #这里计算出self.IDs_mp
        posArray, speedArray = self.compute_multi_emergency_obs()

        speedArray=(np.array(speedArray)/self.norm_speed).tolist()

        lanes = self.ilds_in
        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            d_sum=len(self.IDs_mp[lane])
            waitTime=0
            IDs = self.IDs_mp[lane]
            for i in range(len(IDs)):
                vc = IDs[i]
                waitTime+=self.sim.vehicle.getWaitingTime(vc)

            if d_sum==0:
                self.lane_meanWait[laneIdx]=0
            else:
                self.lane_meanWait[laneIdx]=waitTime*1.0/d_sum

        self.lane_meanWait=(np.array(self.lane_meanWait)/self.norm_wait).tolist()
        return phase_id, posArray, speedArray, density, queue,self.lane_meanWait



    #更加精简
    def compute_multi_emergency_obs(self):
        lanes = self.ilds_in

        posArray=[]
        speedArray=[]

        self.last_action_EVs = self.cur_action_EVs
        self.cur_action_EVs=[]

        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]

            pArray=[0]
            sArray=[0]

            IDs = self.sim.lanearea.getLastStepVehicleIDs(lane)
            self.IDs_mp[lane]=IDs
            for i in range(len(IDs)):
                vc = IDs[i]

                if vc.find("emergency") != -1:

                    self.cur_action_EVs.append(vc)
                    if self.sim.vehicle.getLaneID(vc).find(":")!=-1:
                        continue
                    speed = self.sim.vehicle.getSpeed(vc)
                    pArray[0]=1
                    sArray[0]=speed

            posArray=posArray+pArray
            speedArray=speedArray+sArray
        # if self.name=="t_1_5":
        #     print(self.cur_action_EVs)
        return posArray,speedArray

    def get_edge_hasev(self,sec):

        edge_hasev=[0 for edge in self.tot_neighbor]
        for ev in self.cur_action_EVs:
            if ev in self.comingInfo:
                del self.comingInfo[ev]

        #删除不来的救护车
        for ev in self.comingInfo.copy().keys():
            last_sec=self.comingInfo[ev]['sec']
            if sec-last_sec>30:
                del self.comingInfo[ev]

        for ev in self.comingInfo.keys():
            edge=self.comingInfo[ev]['edge']
            idx = self.tot_neighbor.index(edge.split('-')[0])
            edge_hasev[idx]=1
        return edge_hasev


    def get_lane_hasev(self,sec):

        lane_hasev=[0 for lane in self.ilds_in]
        for ev in self.cur_action_EVs:
            if ev in self.comingInfo:
                del self.comingInfo[ev]

        #删除不来的救护车
        for ev in self.comingInfo.copy().keys():
            last_sec=self.comingInfo[ev]['sec']
            if sec-last_sec>30:
                del self.comingInfo[ev]

        for ev in self.comingInfo.keys():
            ev_coming_lanes=self.comingInfo[ev]['lanes']
            for ev_coming_lane in ev_coming_lanes:
                idx = self.ilds_in.index(ev_coming_lane)
                lane_hasev[idx]=1
        return lane_hasev


    def update_lane_hasev(self):
        lane_hasev=[0 for lane in self.ilds_in]
        for ev in self.comingInfo.keys():
            ev_coming_lanes=self.comingInfo[ev]['lanes']
            for ev_coming_lane in ev_coming_lanes:
                idx = self.ilds_in.index(ev_coming_lane)
                lane_hasev[idx]=1
        self.last_lane_hasev = lane_hasev


    def getNextCommInfo_judge(self):
        info={}

        for vc in self.hasJudgedEV.keys():
            if vc not in self.hasSendEV:
                self.hasSendEV.append(vc)
                action=self.hasJudgedEV[vc]
                chs = self.getJudgeOneHot(action)
                # print(vc)
                # print(action)
                # print(chs)

                for idx in range(len(chs)):
                    if chs[idx]==1:
                        judge_node=self.tot_neighbor[idx]
                        to_node=judge_node

                        f_e=self.name+'-'+to_node
                        f_l_n = self.sim.edge.getLaneNumber(f_e)
                        f_lanes=[]
                        for f_i in range(f_l_n):
                            f_lane = f_e + "_" + str(f_i)
                            f_lanes.append(f_lane)
                        if to_node not in info:
                            info[to_node]=[]
                        info[to_node].append({'lanes':f_lanes, 'edge':f_e, 'ev':vc})
                #print(self.name)
                #print(info)

        return info


    def getNextCommInfo(self):
        info={}
        for vc in self.cur_action_EVs:
            route = self.sim.vehicle.getRoute(vc)
            vc_e = self.sim.vehicle.getRoadID(vc)
            if vc_e not in route:
                continue
            r_idx = route.index(self.sim.vehicle.getRoadID(vc))
            #边界条件
            if r_idx+2>=len(route):
                continue

            f_e = route[r_idx + 1]
            to_node=f_e.split('-')[1]

            t_e = route[r_idx + 2]
            f_l_n = self.sim.edge.getLaneNumber(f_e)
            for f_i in range(f_l_n):
                f_lane = f_e + "_" + str(f_i)
                # print(f_lane)
                links = self.sim.lane.getLinks(f_lane)
                # print(links)
                for link in links:
                    if self.sim.lane.getEdgeID(link[0]) == t_e:
                        if to_node not in info:
                            info[to_node]=[]

                        info[to_node].append({'lanes':[f_lane], 'edge':f_e, 'ev':vc})

                        # print("=====")
                        # print(self.name)
                        # print(to_node)
                        # print(f_lane)
                        # print("=====")
        return info


    def _social_reward(self):
        lanes = self.ilds_in
        C=20
        eta=1
        rho=2
        N=0
        sum=0
        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            IDs = self.sim.lane.getLastStepVehicleIDs(lane)

            for i in range(len(IDs)):
                vc = IDs[i]
                k=self.sim.vehicle.getWaitingTime(vc)
                sum+=eta*(1-(k/C)**rho)
                N+=1
        if N==0:
            return 0

        return sum/N

    #queue+wait
    def _social_reward2(self):
        lanes = self.ilds_in
        q_sum=0
        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]
            q=self.sim.lanearea.getLastStepHaltingNumber(lane)
            q_sum+=q
        wait_reward=np.array(self.lane_meanWait).sum()
        # #print(self.name)
        # if self.name=="t_2_5":
        #     print(q_sum)
        #     print(50*wait_reward/8)

        return -0.3 * (0.5 * q_sum + 50 * wait_reward / 8)


    def _multi_emergency_speed_reward(self):
        reward=0

        for ev in self.last_action_EVs:
            if ev not in self.cur_action_EVs:
                reward+=20

        for ev in self.cur_action_EVs:

            speed = self.sim.vehicle.getSpeed(ev)
            if speed < 1:
                reward+= -20
            else:
                reward+= speed
            #reward += speed
            waitTime=self.sim.vehicle.getWaitingTime(ev)
            reward-=waitTime

        return reward


    def getReward(self,a):

        reward = 0
        social=self._social_reward2()
        emergency=self._multi_emergency_speed_reward()

        # if self.name=="t_1_1":
        #     print(social)
        #     print(emergency)
        reward = emergency+social

        # print(self.name)
        # print(self.last_lane_hasev)

        # for i in range(len(self.last_lane_hasev)):
        #     if self.last_lane_hasev[i]==1:
        #         idx=self.lanes_in.index(self.ilds_in[i])
        #         if self.phases[a][idx] in 'gG':
        #             reward+=5

        if "combine" in self.mode:
            tot_edge=[]
            for i in range(len(self.last_lane_hasev)):

                if self.last_lane_hasev[i]==1:
                    f_e=self.sim.lane.getEdgeID(self.ilds_in[i])
                    if f_e in tot_edge:
                        continue
                    tot_edge.append(f_e)

                    f_l_n = self.sim.edge.getLaneNumber(f_e)
                    ok=1
                    #每个将要来的车道被绿灯覆盖才奖励
                    for f_i in range(f_l_n):
                        f_lane = f_e + "_" + str(f_i)
                        idx=self.lanes_in.index(f_lane)
                        if self.phases[a][idx] not in 'gG':
                            ok=0
                    if ok==1:
                        reward += 10
                        # print(self.name)
                        # print(self.last_lane_hasev)
                        # print("ok")


        # print(self.name)
        # print(reward)
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


    def detectNewEV(self):
        lanes = self.ilds_in

        for laneIdx in range(len(lanes)):
            lane=lanes[laneIdx]

            IDs = self.sim.lanearea.getLastStepVehicleIDs(lane)

            for i in range(len(IDs)):
                vc = IDs[i]
                if vc.find("emergency") != -1:
                    lane = self.sim.vehicle.getLaneID(vc)
                    if lane.find(":") != -1:
                        continue
                    if vc not in self.hasJudgedEV and vc not in self.notJudgedEV:
                        # print(self.name)
                        # print(vc)
                        self.notJudgedEV.append(vc)
                        # if "emergency1" in vc:
                        #     print(vc)
                        #     lane=self.sim.vehicle.getLaneID(vc)
                        #     print(lane)


    #记录下已经判断过的ev的路径
    def recordRoute(self):
        for e in self.tot_ev.copy():
            try:
                edge = self.sim.vehicle.getRoadID(e)
                if edge=="":
                    continue

                if e not in self.hasJudgedEV_route:
                    self.hasJudgedEV_route[e] = []
                if ":" not in edge and edge not in self.hasJudgedEV_route[e]:
                    self.hasJudgedEV_route[e].append(edge)
            except:
                self.tot_ev.remove(e)


    def apply_action(self,action):
        for ev in action.keys():
            self.notJudgedEV.remove(ev)
            self.hasJudgedEV[ev]=action[ev]
            self.hasJudgedEV_route[ev]=[]
            self.tot_ev.add(ev)


    def getJudgeOneHot(self,a):
        m = [0, 0, 0, 0]
        idx = 0
        while a > 0:
            m[idx] = a % 2  # a对2求余，添加到字符串m最后
            a = a // 2
            idx += 1
        return m

    def getJudgeReward(self):

        reward={}
        for ev in self.hasJudgedEV.keys():
            if ev not in self.tot_judge_reward:
                action=self.hasJudgedEV[ev]
                route=self.hasJudgedEV_route[ev]
                chs=self.getJudgeOneHot(action)
                if len(route)<=1:
                    break

                to_node=route[1].split('-')[1]
                #绝对不会到达的节点
                not_node=route[0].split('-')[0]
                # print(ev)
                # print(action)
                # print(route)
                # print(chs)
                # print(to_node)
                # print(self.tot_neighbor)

                r=0
                for idx in range(len(chs)):
                    if chs[idx]==1:
                        judge_node=self.tot_neighbor[idx]
                        #对绝不可能到达的节点直接惩罚
                        if judge_node==not_node:
                            r=-1
                            break
                        #奖励到达的节点
                        if judge_node==to_node:
                            r+=1
                        #
                        if judge_node!=to_node:
                            r-=0.2
                reward[ev]=r
                self.tot_judge_reward[ev]=r

                judge_nodes = []
                for idx in range(len(chs)):
                    if chs[idx]==1:
                        judge_node = self.tot_neighbor[idx]
                        judge_nodes.append(judge_node)

                if to_node in judge_nodes:
                    self.ev_cover[ev]=1
                    self.ev_waste[ev]=(len(judge_nodes)-1)/len(judge_nodes)
                else:
                    self.ev_cover[ev]=0
                    self.ev_waste[ev]=1
        return reward

    def getJudgeState(self):
        state={}
        for vc in self.notJudgedEV:
            #print(vc)
            lane=self.sim.vehicle.getLaneID(vc)

            idx=self.ilds_in.index(lane)
            posArray=[0 for i in range(len(self.ilds_in))]
            posArray[idx]=1
            typeArray=self.compute_type_obs(vc)
            # print(posArray)
            # print(typeArray)
            state[vc]=posArray+typeArray

            for neighbor in self.neighbor:
                f_e=self.name+'-'+neighbor
                f_l_n = self.sim.edge.getLaneNumber(f_e)
                tot_density=0
                for f_i in range(f_l_n):
                    f_lane = f_e + "_" + str(f_i)
                    lanearea_length=self.sim.lanearea.getLength(f_lane)
                    tot_density+=min(1, self.sim.lanearea.getLastStepVehicleNumber(f_lane) / (lanearea_length / self.vehicle_size_min_gap))

                density=tot_density/f_l_n
                state[vc]=state[vc]+[density]

            #print(vc)
            #print(state[vc])

        return state

    def compute_type_obs(self,vc):
        ob=[0,0,0]
        if "emergency1" in vc:
            ob[0]=1
        elif "emergency2" in vc:
            ob[1]=1
        elif "emergency3" in vc:
            ob[2]=1
        return ob

