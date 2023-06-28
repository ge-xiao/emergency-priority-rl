import json
import os
with open("./roadnet_16_3.json", "r", encoding="utf-8") as f:
    netJson = json.load(f)
    #print(netJson)
with open("./anon_16_3_newyork_real.json", "r", encoding="utf-8") as f:
    flowJson = json.load(f)

ev_flow = 15
num_ev=4

intersections=netJson['intersections']
nodeName={}
for node in intersections:
    if node["width"]==0:
        nodeName[node['id']]=node['id'].replace("intersection","p")
    else:
        nodeName[node['id']]=node['id'].replace("intersection","t")
edgeName={}
roads=netJson['roads']
for road in roads:
    edgeName[road['id']]=nodeName[road['startIntersection']]+'-'+nodeName[road['endIntersection']]



def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)


def nodeType(name):
    pass


def output_nodes():
    str_nodes = '<nodes>\n'
    template = '  <node id="%s" x="%.2f" y="%.2f" type="%s"/>\n'
    for node in intersections:
        name=nodeName[node['id']]
        if node["width"]==0:

            str_nodes += template % (name, node['point']['x'], node['point']['y'], 'priority')
        else:
            str_nodes += template % (name, node['point']['x'], node['point']['y'], 'traffic_light')

    str_nodes += '</nodes>\n'
    return str_nodes

def output_edges():
    str_edges = '<edges>\n'

    template = '  <edge id="%s" from="%s" to="%s" numLanes="%s" speed="20"/>\n'

    for road in roads:
        numlane=len(road['lanes'])
        str_edges+=template %(edgeName[road['id']],nodeName[road['startIntersection']],nodeName[road['endIntersection']],numlane)
    str_edges += '</edges>\n'
    return str_edges

def output_netconfig():
    str_config = '<configuration>\n  <input>\n'
    str_config += '    <edge-files value="exp.edg.xml"/>\n'
    str_config += '    <node-files value="exp.nod.xml"/>\n'

#    str_config += '    <tllogic-files value="exp.tll.xml"/>\n'
    str_config += '    <connection-files value="exp.con.xml"/>\n'
    str_config += '  </input>\n  <output>\n'
    str_config += '    <output-file value="exp.net.xml"/>\n'
    str_config += '  </output>\n</configuration>\n'
    return str_config

#和sumo中的lane的标号不太一样
def convertLaneIdx(idx):
    if idx==0:
        return 2
    elif idx==2:
        return 0
    else:
        return idx

def output_connections():
    str_cons = '<connections>\n'

    con = '  <connection from="%s" to="%s" fromLane="%d" toLane="%d"/>\n'
    for node in intersections:
        roadLinks=node['roadLinks']
        for roadLink in roadLinks:
            startEdge=edgeName[roadLink['startRoad']]
            endEdge=edgeName[roadLink['endRoad']]
            laneLinks=roadLink['laneLinks']
            for laneLink in laneLinks:
                str_cons+=con%(startEdge,endEdge,convertLaneIdx(laneLink['startLaneIndex']),convertLaneIdx(laneLink['endLaneIndex']))

    str_cons += '</connections>\n'
    return str_cons


four_phases=[
    #'GGGrrrrrrGGGrrrrrrGGGrrrrrrGGGrrrrrr',
    'GGGrrrrrrGGGGGGrrrGGGrrrrrrGGGGGGrrr',
    'GGGrrrrrrGGGyyyrrrGGGrrrrrrGGGyyyrrr',

    'GGGGGGrrrGGGrrrrrrGGGGGGrrrGGGrrrrrr',
    'GGGyyyrrrGGGrrrrrrGGGyyyrrrGGGrrrrrr',

    'GGGrrrrrrGGGrrrGGGGGGrrrrrrGGGrrrGGG',
    'GGGrrrrrrGGGrrryyyGGGrrrrrrGGGrrryyy',

    'GGGrrrGGGGGGrrrrrrGGGrrrGGGGGGrrrrrr',
    'GGGrrryyyGGGrrrrrrGGGrrryyyGGGrrrrrr',

]
tot_phases=[
    'GGGrrrrrrGGGGGGrrrGGGrrrrrrGGGGGGrrr',
    'GGGGGGrrrGGGrrrrrrGGGGGGrrrGGGrrrrrr',
    'GGGrrrrrrGGGrrrGGGGGGrrrrrrGGGrrrGGG',
    'GGGrrrGGGGGGrrrrrrGGGrrrGGGGGGrrrrrr',
    'GGGGGGGGGGGGrrrrrrGGGrrrrrrGGGrrrrrr',
    'GGGrrrrrrGGGGGGGGGGGGrrrrrrGGGrrrrrr',
    'GGGrrrrrrGGGrrrrrrGGGGGGGGGGGGrrrrrr',
    'GGGrrrrrrGGGrrrrrrGGGrrrrrrGGGGGGGGG',
]

def output_tls(ids,phases):
    tls = '  <tlLogic id="%s" programID="1" offset="0" type="static">\n'
    phase = '    <phase duration="%d" state="%s"/>\n'

    tls_str = ''

    #phase_duration = [30, 3]
    phase_duration = [5, 2]
    for id in ids:
        node = id
        tls_str += tls % node
        for k, p in enumerate(phases):
            tls_str += phase % (phase_duration[k % 2], p)
        tls_str += '  </tlLogic>\n'
    return tls_str


def outputTls_adds():
    str_adds=""

    for node in intersections:
        name=nodeName[node['id']]
        if 't' in name:
            str_adds+=output_tls([name],four_phases)
    return str_adds


def outputTrafficInfo():
    info = {}
    info['sorted_nodes']=[]
    for node in intersections:
        name=nodeName[node['id']]
        if 't' in name:
            info['sorted_nodes'].append(name)


    info['outEdges']=[]
    for road in roads:
        edge=edgeName[road['id']]
        f_n=edge.split('-')[0]
        t_n=edge.split('-')[1]
        if 'p' in f_n:
            info['outEdges'].append(edge)


    info["phases"]=tot_phases
    neighbor_map = {}
    tot_neighbor_map={}

    for name in info['sorted_nodes']:
        neighbor_map[name]=[]
        tot_neighbor_map[name]=[]

        for road in roads:
            edge=edgeName[road['id']]
            f_n=edge.split('-')[0]
            t_n=edge.split('-')[1]
            if f_n == name:
                if 't' in t_n:
                    neighbor_map[name].append(t_n)
                tot_neighbor_map[name].append(t_n)
    info['tot_neighbor_map'] = tot_neighbor_map
    info['neighbor_map'] = neighbor_map

    with open('trafficInfo.json', 'w', encoding='utf-8') as b:
        # ensure_ascii 显示中文，不以ASCII的方式显示
        json.dump(info, b, ensure_ascii=False, indent=2)  # indent 缩进




def output_ild():
    with open('trafficInfo.json', encoding='utf-8') as a:
        trafficInfo = json.load(a)
    neighbor_map=trafficInfo['neighbor_map']
    str_adds=''
    ild = '  <laneAreaDetector file="NUL" freq="1" id="%s_%d" lane="%s_%d" pos="-60" endPos="-1"/>\n'

    for k,v in neighbor_map.items():
        for node in v:
            edge=k+'-'+node
            for i in range(3):
                str_adds += ild % (edge, i, edge, i)
            
    outEdges=trafficInfo['outEdges']
    for edge in outEdges:
        for i in range(3):
                str_adds += ild % (edge, i, edge, i)


    ild_in='<inductionLoop file="NUL" freq="1" id="%s_%d" lane="%s_%d" pos="10"/>\n'
    outEdges=trafficInfo['outEdges']
    for edge in outEdges:
        for i in range(3):
                str_adds += ild_in % (edge, i, edge, i)

    return str_adds


def output_config():
    out_file = 'exp.rou.xml'
    if num_ev>0:
        out_file = 'exp_%d.rou.xml' % int(num_ev)
    str_config = '<configuration>\n  <input>\n'
    str_config += '    <net-file value="exp.net.xml"/>\n'
    str_config += '    <route-files value="%s"/>\n' % out_file
    str_config += '    <additional-files value="exp.add.xml"/>\n'
    str_config += '  </input>\n  <time>\n'
    str_config += '    <begin value="0"/>\n    <end value="3600"/>\n'
    str_config += '  </time>\n</configuration>\n'
    return str_config

evIDs=[i for i in range(20)]
a_1=0
a_2=0
a_3=0


def addEV(type,start):
    global a_1,a_2,a_3
    strAdd=""
    if type=="emergency1":
        strAdd= '  <trip id="emergency1.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency1"/>\n' % (
            str(evIDs[a_1]),start,'p_4_1-t_3_1', 't_1_16-p_0_16')
        a_1+=1
    if type=="emergency2":
        strAdd= '  <trip id="emergency2.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency2"/>\n' % (
            str(evIDs[a_2]),start,'p_3_17-t_3_16', 't_2_1-p_2_0')
        a_2+=1
    if type=="emergency3":
        strAdd= '  <trip id="emergency3.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency3"/>\n' % (
            str(evIDs[a_3]),start,'p_2_17-t_2_16', 't_2_13-t_2_12')
        a_3+=1

    return strAdd


def output_flows():
    str_flows = '<routes>\n'
    str_flows += '  <vType id="type1" length="5" maxSpeed="11" accel="5" minGap="2.5" decel="10"/>\n'
    str_flows += '  <vType id="emergency1" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="emergency"/>\n'
    str_flows += '  <vType id="emergency2" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="firebrigade"/>\n'
    str_flows += '  <vType id="emergency3" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="police"/>\n'



    k=0
    add_ev=False
    cases=[0 for i in range(10)]
    for flow in flowJson:
        startTime=flow['startTime']
        if startTime>1200:
            break
        if num_ev<0:
            if startTime>600 and add_ev==False:

                str_flows += '  <flow id="emergency1" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency1"/>\n' % ('p_4_1-t_3_1', 't_1_16-p_0_16', ev_flow)
                str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency2"/>\n' % ('p_3_17-t_3_16', 't_2_1-p_2_0', ev_flow)
                str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency3"/>\n' % ('p_2_17-t_2_16', 't_2_13-t_2_12', ev_flow)
                add_ev=True



        elif num_ev==1:
            if startTime == 0 and cases[0]==0:
                str_flows += '  <flow id="emergency1" departPos="base" departLane="best" from="%s" to="%s" begin="0" end="1" vehsPerHour="%s" type="emergency1"/>\n' % ('p_4_1-t_3_1', 't_1_16-p_0_16', ev_flow)
                cases[0] = 1

            if startTime == 500 and cases[1]==0:
                str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="500" end="501" vehsPerHour="%s" type="emergency2"/>\n' % ('p_3_17-t_3_16', 't_2_1-p_2_0', ev_flow)
                cases[1] = 1

            if startTime == 1001 and cases[2]==0:
                str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="1000" end="1001" vehsPerHour="%s" type="emergency3"/>\n' % ('p_2_17-t_2_16', 't_2_13-t_2_12', ev_flow)
                cases[2] = 1


        elif num_ev==2:
            if startTime == 0 and cases[3]==0:
                str_flows += '  <trip id="emergency1.0" departPos="base" departLane="best" depart="0"  from="%s" to="%s" type="emergency1"/>\n' % ('p_4_1-t_3_1', 't_1_16-p_0_16')

                str_flows += '  <trip id="emergency2.0" departPos="base" departLane="best" depart="0"  from="%s" to="%s" type="emergency2"/>\n' % ('p_3_17-t_3_16', 't_2_1-p_2_0')
                cases[3] = 1

            if startTime == 500 and cases[4]==0:
                str_flows += '  <trip id="emergency1.1" departPos="base" departLane="best" depart="500"  from="%s" to="%s" type="emergency1"/>\n' % ('p_4_1-t_3_1', 't_1_16-p_0_16')

                str_flows += '  <trip id="emergency3.0" departPos="base" departLane="best" depart="500"  from="%s" to="%s" type="emergency3"/>\n' % ('p_2_17-t_2_16', 't_2_13-t_2_12')
                cases[4] = 1

            if startTime == 1001 and cases[5]==0:
                str_flows += '  <trip id="emergency2.1" departPos="base" departLane="best" depart="1000"  from="%s" to="%s" type="emergency2"/>\n' % ('p_3_17-t_3_16', 't_2_1-p_2_0')

                str_flows += '  <trip id="emergency3.1" departPos="base" departLane="best" depart="1000"  from="%s" to="%s" type="emergency3"/>\n' % ('p_2_17-t_2_16', 't_2_13-t_2_12')
                cases[5] = 1

        elif num_ev==4:
            if startTime == 0 and cases[3]==0:
                str_flows +=addEV("emergency1",0)
                str_flows +=addEV("emergency2",0)
                str_flows +=addEV("emergency3",0)
                cases[3] = 1

            if startTime == 50 and cases[6]==0:
                str_flows +=addEV("emergency1",50)
                cases[6] = 1

            if startTime == 500 and cases[4]==0:
                str_flows +=addEV("emergency1",500)
                str_flows +=addEV("emergency2",500)
                str_flows +=addEV("emergency3",500)
                cases[4] = 1

            if startTime == 551 and cases[7]==0:
                str_flows +=addEV("emergency2",550)
                cases[7] = 1

            if startTime == 1001 and cases[5]==0:
                str_flows +=addEV("emergency1",1000)
                str_flows +=addEV("emergency2",1000)
                str_flows +=addEV("emergency3",1000)
                cases[5] = 1

            if startTime == 1051 and cases[8]==0:
                str_flows +=addEV("emergency3",1050)
                cases[8] = 1



        route=flow['route']
        route_str=""
        for e in route:
            route_str+=edgeName[e]+" "


        str_flows += '  <vehicle  id="%s" departPos="base" departLane="best" depart="%.2f" type="type1">\n' % (
        str(k), startTime)
        str_flows += '    <route edges="%s"/>\n' %(route_str)
        str_flows += '  </vehicle >\n'
        k += 1


    str_flows += '</routes>\n'
    return str_flows






def main():

    write_file('./exp.nod.xml', output_nodes())
    
    
    # edg.xml file
    write_file('./exp.edg.xml', output_edges())

    write_file('./exp.con.xml', output_connections())


    # net config file
    write_file('./exp.netccfg', output_netconfig())

    outputTrafficInfo()



    tot_adds='<additional>\n'

    tot_adds+=outputTls_adds()
    tot_adds+=output_ild()
    #收尾
    tot_adds += '</additional>\n'

    write_file('./exp.add.xml', tot_adds)

    # generate net.xml file
    os.system('netconvert -c exp.netccfg')

    if num_ev<0:
        write_file('./exp.sumocfg', output_config())
    else:
        write_file('./exp_'+str(num_ev)+'.sumocfg', output_config())




    if num_ev<0:
        write_file('./exp.rou.xml', output_flows())
    else:
        write_file('./exp_'+str(num_ev)+'.rou.xml', output_flows())



if __name__ == '__main__':
    main()

