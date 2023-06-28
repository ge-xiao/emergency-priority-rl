import numpy as np
import os

# 200,150
L0 = 200
L0_end = 150
grid_len = 5
SPEED_LIMIT_ST = 20
SPEED_LIMIT_AV = 20
MAX_CAR_NUM = 30
ev_flow = 15
# 300,250
FLOW1 = 250
FLOW2 = 250


def output_road_types():
    str_types = '<types>\n'
    str_types += '  <type id="a" priority="2" numLanes="4" speed="%.2f"/>\n' % SPEED_LIMIT_ST
    str_types += '  <type id="b" priority="1" numLanes="4" speed="%.2f"/>\n' % SPEED_LIMIT_AV
    str_types += '</types>\n'
    return str_types


def getNodePos(x, y):
    if x > 0 and x <= grid_len and y > 0 and y <= grid_len:
        return L0 * (x - 1), L0 * (y - 1)
    if x == 0:
        return -L0_end, (y - 1) * L0
    if y == 0:
        return (x - 1) * L0, -L0_end
    if x == grid_len + 1:
        return (grid_len - 1) * L0 + L0_end, (y - 1) * L0
    if y == grid_len + 1:
        return (x - 1) * L0, (grid_len - 1) * L0 + L0_end


def isNode(x, y):
    if x < 0 or y < 0 or x > grid_len + 1 or y > grid_len + 1:
        return False
    if (x, y) == (0, 0) or (x, y) == (0, grid_len + 1) or (x, y) == (grid_len + 1, 0) or (x, y) == (
            grid_len + 1, grid_len + 1):
        return False
    return True


def nodeType(x, y):
    if x > 0 and x <= grid_len and y > 0 and y <= grid_len:
        return 't'
    else:
        return 'p'


def nodeName(x, y):
    if nodeType(x, y) == 't':
        return 't_' + str(x) + '_' + str(y)
    else:
        return 'p_' + str(x) + '_' + str(y)


traffic_light = []
priority = []


def output_nodes(node):
    str_nodes = '<nodes>\n'
    # traffic light nodes
    for x in range(grid_len + 2):
        for y in range(grid_len + 2):
            dx, dy = getNodePos(x, y)
            if isNode(x, y):
                if nodeType(x, y) == 'p':
                    str_nodes += node % (nodeName(x, y), dx, dy, 'priority')
                else:
                    str_nodes += node % (nodeName(x, y), dx, dy, 'traffic_light')

    str_nodes += '</nodes>\n'
    return str_nodes


def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)


def get_edge_str(edge, from_node, to_node, edge_type):
    edge_id = '%s-%s' % (from_node, to_node)
    return edge % (edge_id, from_node, to_node, edge_type)


def output_edges(edge):
    str_edges = '<edges>\n'
    # external roads
    dx = [0, 0, 1, -1]
    dy = [1, -1, 0, 0]
    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):

            for i in range(4):
                nx = x + dx[i]
                ny = y + dy[i]

                if i == 0 or i == 1:
                    str_edges += get_edge_str(edge, nodeName(x, y), nodeName(nx, ny), 'b')
                    #print(get_edge_str(edge, nodeName(x, y), nodeName(nx, ny), 'b'))
                else:
                    str_edges += get_edge_str(edge, nodeName(x, y), nodeName(nx, ny), 'a')

    for i in range(1, grid_len + 1, 1):
        str_edges += get_edge_str(edge, nodeName(0, i), nodeName(1, i), 'a')
        str_edges += get_edge_str(edge, nodeName(i, 0), nodeName(i, 1), 'b')
        str_edges += get_edge_str(edge, nodeName(grid_len + 1, i), nodeName(grid_len, i), 'a')
        str_edges += get_edge_str(edge, nodeName(i, grid_len + 1), nodeName(i, grid_len), 'b')

    str_edges += '</edges>\n'

    return str_edges


def get_con_str(con, from_node, cur_node, to_node, from_lane, to_lane):
    from_edge = '%s-%s' % (from_node, cur_node)
    to_edge = '%s-%s' % (cur_node, to_node)
    return con % (from_edge, to_edge, from_lane, to_lane)


def get_con_str_set(con, cur_node, n_node, s_node, w_node, e_node):
    str_cons = ''
    # go-through
    str_cons += get_con_str(con, s_node, cur_node, n_node, 1, 1)
    str_cons += get_con_str(con, n_node, cur_node, s_node, 1, 1)
    str_cons += get_con_str(con, w_node, cur_node, e_node, 1, 1)
    str_cons += get_con_str(con, e_node, cur_node, w_node, 1, 1)
    # left-turn
    str_cons += get_con_str(con, s_node, cur_node, w_node, 2, 2)
    str_cons += get_con_str(con, n_node, cur_node, e_node, 2, 2)
    str_cons += get_con_str(con, w_node, cur_node, n_node, 2, 2)
    str_cons += get_con_str(con, e_node, cur_node, s_node, 2, 2)
    # right-turn
    str_cons += get_con_str(con, s_node, cur_node, e_node, 1,1)
    str_cons += get_con_str(con, n_node, cur_node, w_node, 1,1)
    str_cons += get_con_str(con, w_node, cur_node, s_node, 1,1)
    str_cons += get_con_str(con, e_node, cur_node, n_node, 1,1)
    return str_cons


def output_connections(con):
    str_cons = '<connections>\n'
    # edge nodes
    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):
            str_cons += get_con_str_set(con, nodeName(x, y), nodeName(x, y + 1), nodeName(x, y - 1), nodeName(x - 1, y),
                                        nodeName(x + 1, y))

    str_cons += '</connections>\n'
    return str_cons


four_phases = ['GGrrrrGGrrrr',
               'rrGrrrrrGrrr',
               'rrrGGrrrrGGr',
               'rrrrrGrrrrrG',
               "GGGrrrrrrrrr",
               "rrrGGGrrrrrr",
               "rrrrrrGGGrrr",
               "rrrrrrrrrGGG"]

tot_phases = ['GGrrrrGGrrrr', 'yyrrrryyrrrr',
              'rrGrrrrrGrrr', 'rryrrrrryrrr',
              'rrrGGrrrrGGr', 'rrryyrrrryyr',
              'rrrrrGrrrrrG', 'rrrrryrrrrry']


def output_tls(tls, phase):
    str_adds = '<additional>\n'

    #phase_duration = [30, 3]
    phase_duration = [30, 2]
    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):
            node = nodeName(x, y)
            str_adds += tls % node
            for k, p in enumerate(tot_phases):
                # print(k)
                # print(p)
                str_adds += phase % (phase_duration[k % 2], p)
            str_adds += '  </tlLogic>\n'
    str_adds += '</additional>\n'
    return str_adds


def output_netconfig():
    str_config = '<configuration>\n  <input>\n'
    str_config += '    <edge-files value="exp.edg.xml"/>\n'
    str_config += '    <node-files value="exp.nod.xml"/>\n'
    str_config += '    <type-files value="exp.typ.xml"/>\n'
    str_config += '    <tllogic-files value="exp.tll.xml"/>\n'
    str_config += '    <connection-files value="exp.con.xml"/>\n'
    str_config += '  </input>\n  <output>\n'
    str_config += '    <output-file value="exp.net.xml"/>\n'
    str_config += '  </output>\n</configuration>\n'
    return str_config


def edgeName(x1, y1, x2, y2):
    return nodeName(x1, y1) + '-' + nodeName(x2, y2)


def edgeNameByIdx(dir, idx, start):
    if dir == 'n':
        if start:
            return edgeName(idx, grid_len + 1, idx, grid_len)
        else:
            return edgeName(idx, grid_len, idx, grid_len + 1)

    if dir == 'w':
        if start:
            return edgeName(0, idx, 1, idx)
        else:
            return edgeName(1, idx, 0, idx)

    if dir == 's':
        if start:
            return edgeName(idx, 0, idx, 1)
        else:
            return edgeName(idx, 1, idx, 0)

    if dir == 'e':
        if start:
            return edgeName(grid_len + 1, idx, grid_len, idx)
        else:
            return edgeName(grid_len, idx, grid_len + 1, idx)


def output_flows(peak_flow1, peak_flow2, density, seed=None):
    if seed is not None:
        np.random.seed(seed)
    ext_flow = '  <flow id="f_%s" departPos="base" departLane="best" from="%s" to="%s" begin="%d" end="%d" vehsPerHour="%d" type="type1">\n  </flow>\n'
    str_flows = '<routes>\n'
    str_flows += '  <vType id="type1" length="5" maxSpeed="11" accel="5" minGap="2.5" decel="10"/>\n'
    str_flows += '  <vType id="emergency1" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="emergency"/>\n'
    str_flows += '  <vType id="emergency2" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="firebrigade"/>\n'
    str_flows += '  <vType id="emergency3" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="police"/>\n'
    # str_flows += '  <flow id="emergency1" departPos="base" departLane="best" begin="0" end="3000" vehsPerHour="%s" type="emergency">\n' % (
    #     ev_flow)
    # str_flows += '    <route edges="p_4_3-t_3_3 t_3_3-t_2_3 t_2_3-t_2_2 t_2_2-t_2_1 t_2_1-t_1_1 t_1_1-p_1_0"/>\n'
    # str_flows += '  </flow>\n'

    # str_flows += '  <flow id="emergency2" departPos="base" departLane="best" begin="0" end="3000" vehsPerHour="%s" type="emergency">\n' % (
    #     ev_flow)
    # str_flows += '    <route edges="p_0_2-t_1_2 t_1_2-t_2_2 t_2_2-t_3_2 t_3_2-p_4_2"/>\n'
    # str_flows += '  </flow>\n'


    # str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="0" end="3000" vehsPerHour="%s" type="emergency"/>\n' % (
    # edgeNameByIdx('w', grid_len, True), edgeNameByIdx('e', 1, False), ev_flow)
    # str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="0" end="3000" vehsPerHour="%s" type="emergency"/>\n' % (
    # edgeNameByIdx('s', 1, True), edgeNameByIdx('n', grid_len, False), ev_flow)
    # str_flows += '  <flow id="emergency4" departPos="base" departLane="best" from="%s" to="%s" begin="0" end="3000" vehsPerHour="%s" type="emergency"/>\n' % (
    # edgeNameByIdx('s', grid_len, True), edgeNameByIdx('n', 1, False), ev_flow)

    # initial traffic dist

    srcs, sinks = [], []
    for i in range(1,6,1):
        srcs.append(edgeNameByIdx('w', i, True))
        sinks.append(edgeNameByIdx('e', 6-i, False))
        srcs.append(edgeNameByIdx('e', i, True))
        sinks.append(edgeNameByIdx('w', 6-i, False))
        srcs.append(edgeNameByIdx('s', i, True))
        sinks.append(edgeNameByIdx('n', 6-i, False))
        srcs.append(edgeNameByIdx('n', i, True))
        sinks.append(edgeNameByIdx('s', 6-i, False))


    # create external origins and destinations for flows

    # create volumes per 5 min for flows
    ratios = np.array([0.8, 1, 0.8])  # start from 0
    times = np.arange(0, 1201, 400)
    flows = peak_flow1 * 1.0 * ratios
    # print(flows)

    for i in range(len(times) - 1):
        name = str(i)
        k = 0
        t_begin, t_end = times[i], times[i + 1]

        # cur_name = name + '_' + str(k)
        # # str_flows += ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[i])
        # str_flows += '  <flow id="%s" departPos="base" departLane="best" begin="%s" end="%s" vehsPerHour="%s" type="type1">\n' % (
        # cur_name, t_begin, t_end, flows[i])
        # str_flows += '    <route edges="p_2_4-t_2_3 t_2_3-t_2_2 t_2_2-t_2_1 t_2_1-p_2_0"/>\n'
        # str_flows += '  </flow>\n'
        # k += 1

        # cur_name = name + '_' + str(k)
        # str_flows += '  <flow id="%s" departPos="base" departLane="best" begin="%s" end="%s" vehsPerHour="%s" type="type1">\n' % (
        # cur_name, t_begin, t_end, flows[i])
        # str_flows += '    <route edges="p_0_3-t_1_3 t_1_3-t_2_3 t_2_3-t_2_2 t_2_2-t_2_1 t_2_1-t_3_1 t_3_1-p_3_0"/>\n'
        # str_flows += '  </flow>\n'
        # k += 1

        if t_begin>400:
            str_flows += '  <flow id="emergency1" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency1"/>\n' % (edgeNameByIdx('w', 5, True), edgeNameByIdx('e', 1, False), ev_flow)
            str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency2"/>\n' % (edgeNameByIdx('s', 3, True), edgeNameByIdx('n', 3, False), ev_flow)
            str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency3"/>\n' % (edgeNameByIdx('e', 3, True), edgeNameByIdx('w', 1, False), ev_flow)



        for e1, e2 in zip(srcs, sinks):
            cur_name = name + '_' + str(k)
            str_flows += ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[i])
            k += 1

    str_flows += '</routes>\n'
    return str_flows


def output_config(thread=None):
    if thread is None:
        out_file = 'exp.rou.xml'
    else:
        out_file = 'exp_%d.rou.xml' % int(thread)
    str_config = '<configuration>\n  <input>\n'
    str_config += '    <net-file value="exp.net.xml"/>\n'
    str_config += '    <route-files value="%s"/>\n' % out_file
    str_config += '    <additional-files value="exp.add.xml"/>\n'
    str_config += '  </input>\n  <time>\n'
    str_config += '    <begin value="0"/>\n    <end value="3600"/>\n'
    str_config += '  </time>\n</configuration>\n'
    return str_config


def output_ild(ild):
    str_adds=""
    dx = [0, 0, 1, -1]
    dy = [1, -1, 0, 0]

    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):

            for i in range(4):
                nx = x + dx[i]
                ny = y + dy[i]
                if nodeType(nx, ny) == 't':
                    edge = '%s-%s' % (nodeName(x, y), nodeName(nx, ny))
                    str_adds += ild % (edge, 1, edge, 1)
                    str_adds += ild % (edge, 2, edge, 2)

    for i in range(1, grid_len + 1, 1):
        edge = '%s-%s' % (nodeName(0, i), nodeName(1, i))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(i, 0), nodeName(i, 1))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(grid_len + 1, i), nodeName(grid_len, i))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(i, grid_len + 1), nodeName(i, grid_len))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)

    return str_adds

def output_ild_in(ild):
    str_adds=""

    dx = [0, 0, 1, -1]
    dy = [1, -1, 0, 0]
    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):

            for i in range(4):
                nx = x + dx[i]
                ny = y + dy[i]
                if nodeType(nx, ny) == 't':
                    edge = '%s-%s' % (nodeName(x, y), nodeName(nx, ny))
                    str_adds += ild % (edge, 1, edge, 1)
                    str_adds += ild % (edge, 2, edge, 2)

    for i in range(1, grid_len + 1, 1):
        edge = '%s-%s' % (nodeName(0, i), nodeName(1, i))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(i, 0), nodeName(i, 1))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(grid_len + 1, i), nodeName(grid_len, i))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
        edge = '%s-%s' % (nodeName(i, grid_len + 1), nodeName(i, grid_len))
        str_adds += ild % (edge, 1, edge, 1)
        str_adds += ild % (edge, 2, edge, 2)
    return str_adds


def main():
    node = '  <node id="%s" x="%.2f" y="%.2f" type="%s"/>\n'
    write_file('./exp.nod.xml', output_nodes(node))

    # typ.xml file
    write_file('./exp.typ.xml', output_road_types())

    # edg.xml file
    edge = '  <edge id="%s" from="%s" to="%s" type="%s"/>\n'
    write_file('./exp.edg.xml', output_edges(edge))

    # con.xml file
    con = '  <connection from="%s" to="%s" fromLane="%d" toLane="%d"/>\n'
    write_file('./exp.con.xml', output_connections(con))

    # tls.xml file
    tls = '  <tlLogic id="%s" programID="0" offset="0" type="static">\n'
    phase = '    <phase duration="%d" state="%s"/>\n'
    write_file('./exp.tll.xml', output_tls(tls, phase))

    # net config file
    write_file('./exp.netccfg', output_netconfig())

    # generate net.xml file
    os.system('netconvert -c exp.netccfg')

    # raw.rou.xml file
    write_file('./exp.rou.xml', output_flows(FLOW1, FLOW2, 0.2))

    # add.xml file
    ild = '  <laneAreaDetector file="NUL" freq="1" id="%s_%d" lane="%s_%d" pos="-60" endPos="-1"/>\n'
    # ild_in = '  <inductionLoop file="ild_out.out" freq="15" id="ild_in:%s" lane="%s_0" pos="10"/>\n'
    ild_in='<inductionLoop file="NUL" freq="1" id="%s_%d" lane="%s_%d" pos="10"/>\n'

    str_adds = '<additional>\n'
    str_adds=str_adds+output_ild(ild)+output_ild_in(ild_in)
    str_adds += '</additional>\n'

    write_file('./exp.add.xml', str_adds)




    # config file
    write_file('./exp.sumocfg', output_config())


import json


def outputNeighbor_map():
    info = {}

    neighbor_map = {}
    tot_neighbor_map={}
    dx = [0, 0, 1, -1]
    dy = [1, -1, 0, 0]
    for x in range(1, grid_len + 1, 1):
        for y in range(1, grid_len + 1, 1):
            neighbor_map[nodeName(x, y)] = []
            tot_neighbor_map[nodeName(x, y)]=[]
            for i in range(4):
                nx = x + dx[i]
                ny = y + dy[i]
                if nodeType(nx, ny) == 't':
                    neighbor_map[nodeName(x, y)].append(nodeName(nx, ny))

                tot_neighbor_map[nodeName(x, y)].append(nodeName(nx, ny))

    # print(neighbor_map)
    info['tot_neighbor_map'] = tot_neighbor_map
    info['neighbor_map'] = neighbor_map
    info['phases'] = four_phases
    #print(info)


    outEdges=[]
    for i in range(1, grid_len + 1, 1):
        edge = '%s-%s' % (nodeName(0, i), nodeName(1, i))
        outEdges.append(edge)
        edge = '%s-%s' % (nodeName(i, 0), nodeName(i, 1))
        outEdges.append(edge)
        edge = '%s-%s' % (nodeName(grid_len + 1, i), nodeName(grid_len, i))
        outEdges.append(edge)
        edge = '%s-%s' % (nodeName(i, grid_len + 1), nodeName(i, grid_len))
        outEdges.append(edge)

    info['outEdges'] = outEdges


    with open('trafficInfo.json', 'w', encoding='utf-8') as b:
        # ensure_ascii 显示中文，不以ASCII的方式显示
        json.dump(info, b, ensure_ascii=False, indent=2)  # indent 缩进


if __name__ == '__main__':
    main()
    outputNeighbor_map()
