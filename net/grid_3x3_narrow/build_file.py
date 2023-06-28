import numpy as np
import os


L0 = 200
L0_end = 75
grid_len=3
SPEED_LIMIT_ST = 20
SPEED_LIMIT_AV = 11
MAX_CAR_NUM = 30


def output_road_types():
    str_types = '<types>\n'
    str_types += '  <type id="a" priority="2" numLanes="2" speed="%.2f"/>\n' % SPEED_LIMIT_ST
    str_types += '  <type id="b" priority="1" numLanes="1" speed="%.2f"/>\n' % SPEED_LIMIT_AV
    str_types += '</types>\n'
    return str_types


def getNodePos(x,y):
    if x>0 and x<=grid_len and y>0 and y<=grid_len:
        return L0*(x-1),L0*(y-1)
    if x==0:
        return -L0_end,(y-1)*L0
    if y==0:
        return (x-1)*L0,-L0_end
    if x==grid_len+1:
        return (grid_len-1)*L0+L0_end,(y-1)*L0
    if y==grid_len+1:
        return (x-1)*L0,(grid_len-1)*L0+L0_end

def isNode(x,y):
    if x<0 or y<0 or x>grid_len+1 or y>grid_len+1:
        return False
    if (x,y)==(0,0) or (x,y)==(0,grid_len+1) or (x,y)==(grid_len+1,0) or (x,y)==(grid_len+1,grid_len+1):
        return False
    return True

def nodeType(x,y):
    if x>0 and x<=grid_len and y>0 and y<=grid_len:
        return 't'
    else:
        return 'p'

def nodeName(x,y):
    if nodeType(x,y)=='t':
        return 't_' + str(x)+'_'+str(y)
    else:
        return 'p_' + str(x)+'_'+str(y)
        


traffic_light=[]
priority=[]


def output_nodes(node):
    str_nodes = '<nodes>\n'
    # traffic light nodes
    for x in range(grid_len+2):
        for y in range(grid_len+2):
            dx,dy=getNodePos(x,y)
            if isNode(x,y):
                if nodeType(x,y)=='p':
                    str_nodes += node % (nodeName(x,y), dx, dy, 'priority')
                else:
                    str_nodes += node % (nodeName(x,y), dx, dy, 'traffic_light')


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
    dx=[0,0,1,-1]
    dy=[1,-1,0,0]
    for x in range(1,grid_len+1,1):
        for y in range(1,grid_len+1,1):

            for i in range(4):
                nx=x+dx[i]
                ny=y+dy[i]

                if i==0 or i==1:
                    str_edges += get_edge_str(edge, nodeName(x,y), nodeName(nx,ny), 'b')
                else:
                    str_edges += get_edge_str(edge, nodeName(x,y), nodeName(nx,ny), 'a')
    
    for i in range(1,grid_len+1,1):
        str_edges += get_edge_str(edge, nodeName(0,i), nodeName(1,i), 'a')
        str_edges += get_edge_str(edge, nodeName(i,0), nodeName(i,1), 'b')
        str_edges += get_edge_str(edge, nodeName(grid_len+1,i), nodeName(grid_len,i), 'a')
        str_edges += get_edge_str(edge, nodeName(i,grid_len+1), nodeName(i,grid_len), 'b')


    str_edges += '</edges>\n'

    return str_edges



def get_con_str(con, from_node, cur_node, to_node, from_lane, to_lane):
    from_edge = '%s-%s' % (from_node, cur_node)
    to_edge = '%s-%s' % (cur_node, to_node)
    return con % (from_edge, to_edge, from_lane, to_lane)


def get_con_str_set(con, cur_node, n_node, s_node, w_node, e_node):
    str_cons = ''
    # go-through
    str_cons += get_con_str(con, s_node, cur_node, n_node, 0, 0)
    str_cons += get_con_str(con, n_node, cur_node, s_node, 0, 0)
    str_cons += get_con_str(con, w_node, cur_node, e_node, 0, 0)
    str_cons += get_con_str(con, e_node, cur_node, w_node, 0, 0)
    # left-turn
    str_cons += get_con_str(con, s_node, cur_node, w_node, 0, 1)
    str_cons += get_con_str(con, n_node, cur_node, e_node, 0, 1)
    str_cons += get_con_str(con, w_node, cur_node, n_node, 1, 0)
    str_cons += get_con_str(con, e_node, cur_node, s_node, 1, 0)
    # right-turn
    str_cons += get_con_str(con, s_node, cur_node, e_node, 0, 0)
    str_cons += get_con_str(con, n_node, cur_node, w_node, 0, 0)
    str_cons += get_con_str(con, w_node, cur_node, s_node, 0, 0)
    str_cons += get_con_str(con, e_node, cur_node, n_node, 0, 0)
    return str_cons


def output_connections(con):
    str_cons = '<connections>\n'
    # edge nodes
    for x in range(1,grid_len+1,1):
        for y in range(1,grid_len+1,1):
            str_cons += get_con_str_set(con, nodeName(x,y), nodeName(x,y+1), nodeName(x,y-1), nodeName(x-1,y), nodeName(x+1,y))

    str_cons += '</connections>\n'
    return str_cons


def output_tls(tls, phase):
    str_adds = '<additional>\n'
    # all crosses have 3 phases
    three_phases = ['GGgrrrGGgrrr', 'yyyrrryyyrrr',
                    'rrrGrGrrrGrG', 'rrrGryrrrGry',
                    'rrrGGrrrrGGr', 'rrryyrrrryyr']
    phase_duration = [30, 3]
    for x in range(1,grid_len+1,1):
        for y in range(1,grid_len+1,1):
            node = nodeName(x,y)
            str_adds += tls % node
            for k, p in enumerate(three_phases):
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


def edgeName(x1,y1,x2,y2):
    return nodeName(x1,y1)+'-'+nodeName(x2,y2)

def edgeNameByIdx(dir,idx,start):
    if dir=='n':
        if start:
            return edgeName(idx,grid_len+1,idx,grid_len)
        else:
            return edgeName(idx,grid_len,idx,grid_len+1)

    if dir=='w':
        if start:
            return edgeName(0,idx,1,idx)
        else:
            return edgeName(1,idx,0,idx)

    if dir=='s':
        if start:
            return edgeName(idx,0,idx,1)
        else:
            return edgeName(idx,1,idx,0)

    if dir=='e':
        if start:
            return edgeName(grid_len+1,idx,grid_len,idx)
        else:
            return edgeName(grid_len,idx,grid_len+1,idx)


def output_flows(peak_flow1, peak_flow2, density, seed=None):
    if seed is not None:
        np.random.seed(seed)
    ext_flow = '  <flow id="f_%s" departPos="random_free" from="%s" to="%s" begin="%d" end="%d" vehsPerHour="%d" type="type1"/>\n'
    str_flows = '<routes>\n'
    str_flows += '  <vType id="type1" length="5" accel="5" minGap="2.5" decel="10"/>\n'
    str_flows+='  <vType id="emergency" length="5" accel="5"  minGap="2.5"  vClass="emergency" guiShape="emergency"/>\n'
    str_flows+='  <flow id="emergency" departPos="random_free" from="%s" to="%s" begin="0" end="3000" vehsPerHour="30" type="emergency"/>\n'%(edgeNameByIdx('w',1,True),edgeNameByIdx('e',grid_len,False))
    # initial traffic dist

    srcs,sinks = [[] for i in range(8)],[[] for i in range(8)]

    l=0
    for idx in range(1,grid_len+1,1):
        srcs[l].append(edgeNameByIdx('n',idx,True))
        sinks[l].append(edgeNameByIdx('s',grid_len+1-idx,False))
    l+=1
    for idx in range(1,grid_len+1,1):
        srcs[l].append(edgeNameByIdx('w',idx,True))
        sinks[l].append(edgeNameByIdx('e',grid_len+1-idx,False))
    l+=1

    # for idx in range(1,grid_len+1,1):
    #     srcs[l].append(edgeNameByIdx('s',idx,True))
    #     sinks[l].append(edgeNameByIdx('n',idx,False))
    # l+=1
    #
    # for idx in range(1,grid_len+1,1):
    #     srcs[l].append(edgeNameByIdx('e',idx,True))
    #     sinks[l].append(edgeNameByIdx('w',idx,False))
    # l+=1


    # create external origins and destinations for flows

    # create volumes per 5 min for flows
    ratios1 = np.array([0.4, 0.7, 0.9, 1.0, 0.75, 0.5, 0.25]) # start from 0
    ratios2 = np.array([0.3, 0.8, 0.9, 1.0, 0.8, 0.6, 0.2])   # start from 15min
    flows1 = peak_flow1 * 0.6 * ratios1
    flows2 = peak_flow1 * ratios1
    flows3 = peak_flow2 * 0.6 * ratios2
    flows4 = peak_flow2 * ratios2
    flows = [flows1, flows2, flows3, flows4]
    times = np.arange(0, 3001, 300)
    id1 = len(flows1)
    id2 = len(times) - 1 - id1

    #print(flows)

    for i in range(len(times) - 1):
        name = str(i)
        t_begin, t_end = times[i], times[i + 1]
        # external flow
        k = 0
        if i < id1:
            for j in [0, 1]:
                for e1, e2 in zip(srcs[j], sinks[j]):

                    cur_name = name + '_' + str(k)
                    str_flows += ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[j][i])
                    #print(ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[j][i]))
                    k += 1
        if i >= id2:
            for j in [2, 3]:
                for e1, e2 in zip(srcs[j], sinks[j]):
                    cur_name = name + '_' + str(k)
                    str_flows += ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[j][i - id2])
                    #print(ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[j][i - id2]))
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
    #str_config += '    <additional-files value="exp.add.xml"/>\n'
    str_config += '  </input>\n  <time>\n'
    str_config += '    <begin value="0"/>\n    <end value="3600"/>\n'
    str_config += '  </time>\n</configuration>\n'
    return str_config

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
    write_file('./exp.rou.xml', output_flows(50, 50, 0.2))

    # config file
    write_file('./exp.sumocfg', output_config())


import json
def outputNeighbor_map():
    neighbor_map={}
    dx=[0,0,1,-1]
    dy=[1,-1,0,0]
    for x in range(1,grid_len+1,1):
        for y in range(1,grid_len+1,1):
            neighbor_map[nodeName(x,y)]=[]

            for i in range(4):
                nx=x+dx[i]
                ny=y+dy[i]
                if nodeType(nx,ny)=='t':
                    neighbor_map[nodeName(x, y)].append(nodeName(nx, ny))

    #print(neighbor_map)

    with open('neighbor_map.json', 'w', encoding='utf-8') as b:
        # ensure_ascii 显示中文，不以ASCII的方式显示
        json.dump(neighbor_map, b, ensure_ascii=False, indent=2)  # indent 缩进

if __name__ == '__main__':
    main()
    #outputNeighbor_map()
