import json

ev_flow = 15
num_ev=4

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)




def outputTls_adds():
    info = {}


    str_adds=""
    info['node_phases']={}

    ids=['t_0','t_1','t_2','t_3','t_4','t_5','t_6','t_7','t_8',
         't_9','t_10','t_11','t_12','t_13','t_14','t_16','t_17']
    
    phases = ['GGGrrrrrGGGrrrrr',
               'yyyrrrrryyyrrrrr',
               'rrrGrrrrrrrGrrrr',
               'rrryrrrrrrryrrrr',
               "rrrrGGGrrrrrGGGr",
               "rrrryyyrrrrryyyr",
               "rrrrrrrGrrrrrrrG",
               "rrrrrrryrrrrrrry"]
    
    tot_phases=['GGGrrrrrGGGrrrrr',
                'rrrGrrrrrrrGrrrr',
                "rrrrGGGrrrrrGGGr",
                "rrrrrrrGrrrrrrrG",
                'GGGGrrrrrrrrrrrr',
                'rrrrGGGGrrrrrrrr',
                'rrrrrrrrGGGGrrrr',
                'rrrrrrrrrrrrGGGG',
                ]
    
    tls_str=output_tls(ids,phases)

    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases
    

    ids=['t_15']
    phases = ['rrrGGGGGGrr',
               'rrryyyyyyrr',
               'rrrrrrrGGGG',
               'rrrrrrryyyy',
               "GGGGrrrrrrr",
               "yyyyrrrrrrr",
                ]
    
    tot_phases=['rrrGGGGGGrr',
                'rrrrrrrGGGG',
                "GGGGrrrrrrr",
                ]

    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases


    ids=['t_18']
    phases = ['GGGrrr',
               'yyyrrr',
               'rrrGGG',
               'rrryyy',
                ]
    
    tot_phases=['GGGrrr',
                'rrrGGG',
                ]

    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases

    

    ids=['t_19']
    phases = ['GGGGrrr',
               'yyyyrrr',
               'rrrrGGG',
               'rrrryyy',
                ]
    
    tot_phases=['GGGGrrr',
                'rrrrGGG',
                ]

    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases


    ids=['t_20']
    phases = ['rrrrrGGrGGGG',
               'rrrrryyryyyy',
               'rrrrrGGGrrrr',
               'rrrrryyyrrrr',
               'GGGGGrrrrrrr',
                'yyyyyrrrrrrr'
                ]
    
    tot_phases=['rrrrrGGrGGGG',
                'rrrrrGGGrrrr',
                'GGGGGrrrrrrr'
                ]
    
    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases


    ids=['t_21']
    phases = ['GGGGrrr',
               'yyyyrrr',
               'rrrrGGG',
               'rrrryyy',
                ]
    
    tot_phases=['GGGGrrr',
                'rrrrGGG',
                ]
    
    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases


    ids=['t_22']
    phases = ['rrrrGGGrGGGr',
               'rrrryyyryyyr',
               'rrrrrrrGrrrG',
               'rrrrrrryrrry',
               'GGGGGrrrrrrr',
               'yyyyyrrrrrrr',
                ]
    
    tot_phases=['rrrrGGGrGGGr',
                'rrrrrrrGrrrG',
                'GGGGGrrrrrrr',
                'rrrrGGGGrrrr',
                'rrrrrrrrGGGG',
                ]
    
    tls_str=output_tls(ids,phases)
    str_adds+=tls_str

    for id in ids:
        info['node_phases'][id]=tot_phases
        
    return str_adds,info
    


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


def outputTrafficInfo(tls_info):
    info = {}
    info['sorted_nodes']=['t_0','t_1','t_2','t_3','t_4','t_5','t_6','t_7','t_8','t_9','t_10','t_11'
                        ,'t_12','t_13','t_14','t_15','t_16','t_17','t_18','t_19','t_20','t_21','t_22']
    neighbor_map = {}
    tot_neighbor_map={}
    neighbor_map['t_0']=['t_1','t_5']
    neighbor_map['t_1']=['t_0','t_2','t_6']
    neighbor_map['t_2']=['t_1','t_3','t_7']
    neighbor_map['t_3']=['t_2','t_4','t_8']
    neighbor_map['t_4']=['t_3','t_9']
    neighbor_map['t_5']=['t_0','t_6','t_10']
    neighbor_map['t_6']=['t_1','t_5','t_7','t_11']
    neighbor_map['t_7']=['t_2','t_6','t_8','t_12']
    neighbor_map['t_8']=['t_3','t_7','t_9','t_13']
    neighbor_map['t_9']=['t_4','t_8','t_14']
    neighbor_map['t_10']=['t_5','t_11','t_18']
    neighbor_map['t_11']=['t_6','t_10','t_12','t_19']
    neighbor_map['t_12']=['t_7','t_11','t_13','t_15']
    neighbor_map['t_13']=['t_8','t_12','t_14','t_16']
    neighbor_map['t_14']=['t_9','t_13','t_17']
    neighbor_map['t_15']=['t_12','t_16','t_20']
    neighbor_map['t_16']=['t_13','t_15','t_17','t_21']
    neighbor_map['t_17']=['t_14','t_16','t_22']
    neighbor_map['t_18']=[]
    neighbor_map['t_19']=['t_11','t_18']
    neighbor_map['t_20']=['t_15','t_19']
    neighbor_map['t_21']=['t_16','t_20']
    neighbor_map['t_22']=['t_17','t_21']

    tot_neighbor_map['t_0']=['t_1','t_5','p_0','p_15']
    tot_neighbor_map['t_1']=['t_0','t_2','t_6','p_1']
    tot_neighbor_map['t_2']=['t_1','t_3','t_7','p_2']
    tot_neighbor_map['t_3']=['t_2','t_4','t_8','p_3']
    tot_neighbor_map['t_4']=['t_3','t_9','p_4','p_5']
    tot_neighbor_map['t_5']=['t_0','t_6','t_10','p_14']
    tot_neighbor_map['t_6']=['t_1','t_5','t_7','t_11']
    tot_neighbor_map['t_7']=['t_2','t_6','t_8','t_12']
    tot_neighbor_map['t_8']=['t_3','t_7','t_9','t_13']
    tot_neighbor_map['t_9']=['t_4','t_8','t_14','p_6']
    tot_neighbor_map['t_10']=['t_5','t_11','t_18','p_13']
    tot_neighbor_map['t_11']=['t_6','t_10','t_12','t_19']
    tot_neighbor_map['t_12']=['t_7','t_11','t_13','t_15']
    tot_neighbor_map['t_13']=['t_8','t_12','t_14','t_16']
    tot_neighbor_map['t_14']=['t_9','t_13','t_17','p_7']
    tot_neighbor_map['t_15']=['t_12','t_16','t_20']
    tot_neighbor_map['t_16']=['t_13','t_15','t_17','t_21']
    tot_neighbor_map['t_17']=['t_14','t_16','t_22','p_8']
    tot_neighbor_map['t_18']=['p_12']
    tot_neighbor_map['t_19']=['t_11','t_18']
    tot_neighbor_map['t_20']=['t_15','t_19','p_11']
    tot_neighbor_map['t_21']=['t_16','t_20']
    tot_neighbor_map['t_22']=['t_17','t_21','p_9','p_10']

    info['tot_neighbor_map'] = tot_neighbor_map
    info['neighbor_map'] = neighbor_map
    
    info['node_phases']=tls_info['node_phases']

    outEdges=[
        'p_0-t_0',
        'p_1-t_1',
        'p_2-t_2',
        'p_3-t_3',
        'p_4-t_4',
        'p_5-t_4',
        'p_6-t_9',
        'p_7-t_14',
        'p_8-t_17',
        'p_9-t_22',
        'p_10-t_22',
        'p_11-t_20',
        'p_12-t_10',
        'p_13-t_10',
        'p_14-t_5',
        'p_15-t_0',
    ]

    info['outEdges'] = outEdges
    

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


import numpy as np

evIDs=[i for i in range(20)]
a_1=0
a_2=0
a_3=0


def addEV(type,start):
    global a_1,a_2,a_3
    strAdd=""
    if type=="emergency1":
        strAdd= '  <trip id="emergency1.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency1"/>\n' % (
            str(evIDs[a_1]),start,'p_4-t_4', 't_18-p_12')
        a_1+=1
    if type=="emergency2":
        strAdd= '  <trip id="emergency2.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency2"/>\n' % (
            str(evIDs[a_2]),start,'p_9-t_22', 't_0-p_0')
        a_2+=1
    if type=="emergency3":
        strAdd= '  <trip id="emergency3.%s" departPos="base" departLane="best" depart="%s"  from="%s" to="%s" type="emergency3"/>\n' % (
            str(evIDs[a_3]),start,'p_13-t_10', 't_14-p_7')
        a_3+=1

    return strAdd

def output_flows(peak_flow1):

    ext_flow = '  <flow id="f_%s" departPos="base" departLane="best" from="%s" to="%s" begin="%d" end="%d" vehsPerHour="%d" type="type1">\n  </flow>\n'
    str_flows = '<routes>\n'
    str_flows += '  <vType id="type1" length="5" maxSpeed="11" accel="5" minGap="2.5" decel="10"/>\n'
    str_flows += '  <vType id="emergency1" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="emergency"/>\n'
    str_flows += '  <vType id="emergency2" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="firebrigade"/>\n'
    str_flows += '  <vType id="emergency3" length="5" accel="5" maxSpeed="20" minGap="2.5"  vClass="emergency" guiShape="police"/>\n'


    e_in=[
        'p_15-t_0',
        'p_14-t_5',
        'p_13-t_10',
    ]
    e_out=[
        't_0-p_15',
        't_5-p_14',
        't_10-p_13'
    ]
    w_in=[
        'p_5-t_4',
        'p_6-t_9',
        'p_7-t_14',
        'p_8-t_17',
        'p_9-t_22',
    ]
    w_out=[
        't_4-p_5',
        't_9-p_6',
        't_14-p_7',
        't_17-p_8',
        't_22-p_9',
    ]
    s_in=[
        'p_0-t_0',
        'p_1-t_1',
        'p_2-t_2',
        'p_3-t_3',
        'p_4-t_4',
    ]
    s_out=[
        't_0-p_0',
        't_1-p_1',
        't_2-p_2',
        't_3-p_3',
        't_4-p_4',
    ]
    n_in=[
        'p_12-t_10',
        'p_11-t_20',
        'p_10-t_22',
    ]
    n_out=[
        't_18-p_12',
        't_20-p_11',
        't_22-p_10',
    ]

    srcs = []
    sinks=[]
    
    for st in s_in:
        for ed in n_out:
           srcs.append(st)
           sinks.append(ed)
    for st in n_in:
        for ed in s_out:
           srcs.append(st)
           sinks.append(ed)    
    for st in w_in:
        for ed in e_out:
           srcs.append(st)
           sinks.append(ed)
    for st in e_in:
        for ed in w_out:
           srcs.append(st)
           sinks.append(ed)

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

        if num_ev<0:
            if t_begin > 400:
                str_flows += '  <flow id="emergency1" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency1"/>\n' % ('p_4-t_4', 't_18-p_12', ev_flow)
                str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency2"/>\n' % ('p_9-t_22', 't_0-p_0', ev_flow)
                str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="600" end="1200" vehsPerHour="%s" type="emergency3"/>\n' % ('p_13-t_10', 't_14-p_7', ev_flow)
        elif num_ev == 1:
            if t_begin == 0:
                str_flows += '  <flow id="emergency1" departPos="base" departLane="best" from="%s" to="%s" begin="0" end="1" vehsPerHour="%s" type="emergency1"/>\n' % ('p_4-t_4', 't_18-p_12', ev_flow)
            if t_begin == 800:
                str_flows += '  <flow id="emergency2" departPos="base" departLane="best" from="%s" to="%s" begin="500" end="501" vehsPerHour="%s" type="emergency2"/>\n' % ('p_9-t_22', 't_0-p_0', ev_flow)

        elif num_ev == 2:
            if t_begin == 0:
                str_flows += '  <trip id="emergency1.0" departPos="base" departLane="best" depart="0"  from="%s" to="%s" type="emergency1"/>\n' % ('p_4-t_4', 't_18-p_12')
                str_flows += '  <trip id="emergency2.0" departPos="base" departLane="best" depart="0"  from="%s" to="%s" type="emergency2"/>\n' % ('p_9-t_22', 't_0-p_0')
            if t_begin == 800:
                str_flows += '  <trip id="emergency1.1" departPos="base" departLane="best" depart="500"  from="%s" to="%s" type="emergency1"/>\n' % ('p_4-t_4', 't_18-p_12')
                str_flows += '  <trip id="emergency3.0" departPos="base" departLane="best" depart="500"  from="%s" to="%s" type="emergency3"/>\n' % ('p_13-t_10', 't_14-p_7')
        if num_ev==4:
            if t_begin == 0:
                str_flows +=addEV("emergency1",0)
                str_flows +=addEV("emergency2",0)
                str_flows +=addEV("emergency3",0)

            if t_begin == 800:
                str_flows +=addEV("emergency1",500)
                str_flows +=addEV("emergency2",500)
                str_flows +=addEV("emergency3",500)
                str_flows +=addEV("emergency2",550)



        for e1, e2 in zip(srcs, sinks):
            cur_name = name + '_' + str(k)
            str_flows += ext_flow % (cur_name, e1, e2, t_begin, t_end, flows[i])
            k += 1

        if num_ev==1:
            if t_begin == 800:
                str_flows += '  <flow id="emergency3" departPos="base" departLane="best" from="%s" to="%s" begin="1000" end="1001" vehsPerHour="%s" type="emergency3"/>\n' % ('p_13-t_10', 't_14-p_7', ev_flow)

        if num_ev == 2:
            if t_begin == 800:
                str_flows += '  <trip id="emergency2.1" departPos="base" departLane="best" depart="1000"  from="%s" to="%s" type="emergency2"/>\n' % ('p_9-t_22', 't_0-p_0')
                str_flows += '  <trip id="emergency3.1" departPos="base" departLane="best" depart="1000"  from="%s" to="%s" type="emergency3"/>\n' % ('p_13-t_10', 't_14-p_7')

        if num_ev==4:
            if t_begin==0:
                str_flows +=addEV("emergency1",50)

            if t_begin == 800:
                str_flows +=addEV("emergency1",1000)
                str_flows +=addEV("emergency2",1000)
                str_flows +=addEV("emergency3",1000)
                str_flows +=addEV("emergency3",1050)

    str_flows += '</routes>\n'
    return str_flows




def main():


    tot_adds='<additional>\n'

    str_adds,info=outputTls_adds()
    tot_adds+=str_adds

    if num_ev<0:
        write_file('./exp.sumocfg', output_config())
    else:
        write_file('./exp_'+str(num_ev)+'.sumocfg', output_config())


    outputTrafficInfo(info)

    str_adds=output_ild()
    tot_adds+=str_adds


    tot_adds += '</additional>\n'
    write_file('./exp.add.xml', tot_adds)

    if num_ev<0:
        write_file('./exp.rou.xml', output_flows(120))
    else:
        write_file('./exp_'+str(num_ev)+'.rou.xml', output_flows(120))

    #write_file('./exp.rou.xml', output_flows(120))

if __name__ == '__main__':
    main()
    #outputNeighbor_map()