
from multiprocessing.connection import wait
import os
import sys
import optparse
import random
import json

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa


def run():
    """execute the TraCI control loop"""
    step = 0

    evSet=set()

    while traci.simulation.getMinExpectedNumber() > 0:

        traci.simulationStep()

        print("========")
        print(step)
        print(traci.simulation.getTime())

        nodes = {}

        for node_name in traci.trafficlight.getIDList():
            #print(node_name)

            nodes[node_name] = 1

        sorted_nodes = sorted(list(nodes.keys()))
        #print(sorted_nodes)

        info = {}
        links_map={}
        for node in sorted_nodes:
            #print(node)
            links=traci.trafficlight.getControlledLinks(node)
            for link in links:
                if link[0][0] not in links_map:
                    #变成一个列表
                    links_map[link[0][0]] = [link[0][1]]
                else:
                    links_map[link[0][0]].append(link[0][1])
                    #print(link[0][0],links_map[link[0][0]])

        print(links_map)
        info['links_map'] = links_map

        tot_ilds_in={}
        for node in sorted_nodes:
            lanes_in = traci.trafficlight.getControlledLanes(node)
            # controlled edges: e:j,i
            # lane ilds: ild:j,i_k for road ji, lane k.
            # edges_in = []
            ilds_in = []
            for lane_name in lanes_in:
                ild_name = lane_name
                if ild_name not in ilds_in:
                    ilds_in.append(ild_name)
            tot_ilds_in[node]=ilds_in
        print(tot_ilds_in)

        for k in tot_ilds_in:
            ilds_in=tot_ilds_in[k]


            #每一个车道对应的可能性
            for ild in ilds_in:
                pos=[]
                to_lanes=func_to_lanes(ild,links_map)
                # print("=====")
                # print(ild)
                # print(to_lanes)
                # print("=====")
                for to_lane in to_lanes:
                    if "p" in to_lane:
                        pos.append([to_lane])
                        continue
                    tto_lanes=func_to_lanes(to_lane,links_map)
                    for tto_lane in tto_lanes:
                        pos.append([to_lane,tto_lane])
                print(ild)
                print(pos)





                # print("=====")
                #
                # print(ild)
                # print(t_edges)
                # print("=====")

        # with open('links_info.json', 'w', encoding='utf-8') as b:
        #     # ensure_ascii 显示中文，不以ASCII的方式显示
        #     json.dump(info, b, ensure_ascii=False, indent=2)  # indent 缩进

        step += 1

    traci.close()
    sys.stdout.flush()

def func_to_lanes(lane,links_map):
    t_lanes = links_map[lane]
    t_edges = []
    to_lanes=[]
    for t_lane in t_lanes:
        t_edge = traci.lane.getEdgeID(t_lane)
        if t_edge not in t_edges:
            t_edges.append(t_edge)
            # 一层要到达的边
    for t_edge in t_edges:
        if "p" in t_edge:
            to_lanes.append(t_edge)
            continue
        t_l_n = traci.edge.getLaneNumber(t_edge)
        for t_i in range(t_l_n):
            # 一层将要到达的车道
            t_lane = t_edge + "_" + str(t_i)
            to_lanes.append(t_lane)
    return to_lanes

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", "exp.sumocfg"])
    run()
