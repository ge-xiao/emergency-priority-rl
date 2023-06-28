from utils.graph import Graph

class Dijkstra_module:
    def __init__(self,sim,trafficInfo,sorted_nodes):
        self.sim=sim
        self.trafficInfo=trafficInfo
        self.sorted_nodes=sorted_nodes
        self.neighbor_map=self.trafficInfo['neighbor_map']
        self.tot_neighbor_map=self.trafficInfo['tot_neighbor_map']
        self.outEdges=self.trafficInfo['outEdges']
        ###Dij
        self.name_idx={}
        for i in range(len(self.sorted_nodes)):
            self.name_idx[self.sorted_nodes[i]]=i


    ###Dij
    def distance(self,f,t):
        e=f+'-'+t
        travel_time=self.sim.lane.getLength(e+'_0')/20
        halt_time=self.sim.edge.getLastStepHaltingNumber(e)
        # if e=='t_1_1-t_2_1':
        #     print(e)
        #     print(halt_time)
        time=travel_time+halt_time
        return time

    ###Dij
    def runDijkstra(self,ev):

        g = Graph(len(self.sorted_nodes))
        edge=self.sim.vehicle.getRoadID(ev)

        for node in self.sorted_nodes:
            for nnode in self.neighbor_map[node]:
                if node==edge.split('-')[1] and nnode==edge.split('-')[0]:
                    continue
                # print(self.name_idx[node],self.name_idx[nnode],0)
                g.add_edge(self.name_idx[node], self.name_idx[nnode], self.distance(node, nnode))

        start_v = self.name_idx[edge.split('-')[1]]
        to_v = self.name_idx[self.ev_endNode[ev]]

        D, previousVertex = g.dijkstra(start_v)
        path=g.path(start_v,to_v,previousVertex)

        real_path=[]
        for p in path:
            real_path.append(self.sorted_nodes[p])

        # print(ev)
        # print("path")
        # print(real_path)
        newRoute=[]
        newRoute.append(edge)
        for i in range(len(real_path)-1):
            to_edge=str(real_path[i])+"-"+real_path[i+1]
            newRoute.append(to_edge)
        newRoute.append(self.ev_endEdge[ev])

        #print(ev,newRoute)

        self.sim.vehicle.setRoute(ev,newRoute)

        #print(ev)
        #route = self.sim.vehicle.getRoute(ev)
        #print(route)

    def directEV(self):
        for ev in self.cur_ev.copy():
            try:
                edge = self.sim.vehicle.getRoadID(ev)
            except:
                self.cur_ev.remove(ev)
                continue

            if edge=="":
                continue
            lane=self.sim.vehicle.getLaneID(ev)
            if lane.find(":") != -1:
                continue
            #到达终点
            if edge==self.ev_endEdge[ev]:
                self.cur_ev.remove(ev)
                continue

            length=self.sim.lane.getLength(lane)
            pos = self.sim.vehicle.getLanePosition(ev)
            toCenter = int(length - pos)


            #距离交叉口180米左右开始判断
            if toCenter<180:
                if ev not in self.hasRunedEV_route or edge not in self.hasRunedEV_route[ev]:

                    self.runDijkstra(ev)

                    if ev not in self.hasRunedEV_route:
                        self.hasRunedEV_route[ev] = []

                    self.hasRunedEV_route[ev].append(edge)


    def run(self):

        ###Dij
        for f_e in self.outEdges:
            f_l_n = self.sim.edge.getLaneNumber(f_e)
            for f_i in range(f_l_n):
                f_lane = f_e + "_" + str(f_i)
                IDs = self.sim.inductionloop.getLastStepVehicleIDs(f_lane)
                for ID in IDs:
                    if "emergency" in ID and ID not in self.tot_ev:
                        route = self.sim.vehicle.getRoute(ID)
                        self.ev_endEdge[ID] = route[len(route) - 1]
                        self.ev_endNode[ID] = route[len(route) - 1].split('-')[0]
                        self.cur_ev.append(ID)
                        self.tot_ev.append(ID)
        self.directEV()



    def reset(self,sim):
        ###Dij
        self.tot_ev=[]
        self.cur_ev=[]
        self.ev_endNode={}
        self.ev_endEdge={}
        self.hasRunedEV_route={}
        self.sim=sim


