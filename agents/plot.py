import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

import xml.etree.cElementTree as ET



def plot_ev(run):
    ev_res = []
    ev_min=15

    for i in range(0, run, 1):
    #for i in range(10, 200, 10):
        #path='../result/output103_im2c/{}/{}_{}/'.format('t_1_1','train',i)
        path='../result/output104_500_ia2c/{}/{}_{}/'.format('t_1_1','train',i)
        df = pd.read_csv(path + 'ev' + '.csv')
        ev_mean = df["waitTime"].mean()
        if ev_mean<ev_min:
            print(i)
            print(ev_mean)

        ev_res.append(ev_mean)

    x = range(len(ev_res))
    plt.plot(x, ev_res)
    plt.show()


def plot_test_ev(run):
    ev_res = []
    ev_min=20

    for i in range(10, run, 10):
        path='../result/output/{}/{}_{}/'.format('t_1_1','test',i)
        df = pd.read_csv(path + 'ev' + '.csv')
        ev_mean = df["waitTime"].mean()
        if ev_mean<ev_min:
            print(i)
            print(ev_mean)

        ev_res.append(ev_mean)

    x = range(len(ev_res))
    plt.plot(x, ev_res)
    plt.show()



def compute_priority(run):
    path = '../result/output/{}/{}_{}/'.format('t_1_1', 'test', run)
    df = pd.read_csv(path + 'ev' + '.csv')
    ev_mean = df["waitTime"].mean()

    print(ev_mean)


def plot_traffic(run):
    path = '../result/output/traffic/'
    df = pd.read_csv(path + ('%s_%s_traffic.csv' % ('evaluate', run)))
    avg_queue_mean=df.avg_queue.rolling(60).mean().values
    plt.plot(df.time_sec.values, avg_queue_mean)


    #plt.plot(df['avg_queue'])
    plt.show()
    avg_wait_sec_mean=df.avg_wait_sec.rolling(60).mean().values
    plt.plot(df.time_sec.values, avg_wait_sec_mean)
    plt.show()

    #plt.plot(df['avg_wait_sec'])
    #plt.show()
    #print(df)


def plot_priority_traffic(path,run):
    path = '../result/'+path+'/total/'
    df = pd.read_csv(path + ('%s_%s_traffic.csv' % ('priority', run)))
    avg_queue_mean=df.avg_queue.rolling(60).mean().values
    plt.plot(df.time_sec.values, avg_queue_mean)
    plt.show()

    avg_wait_sec_mean=df.avg_wait_sec.rolling(60).mean().values
    plt.plot(df.time_sec.values, avg_wait_sec_mean)
    plt.show()


def collect_tripinfo(path,run,mode):
    output_path='../result/'+path+'/trip/'
    trip_file = output_path + (mode+'_%s_trip.xml' % (run))
    tree = ET.ElementTree(file=trip_file)

    ev_trip_data=[]
    for child in tree.getroot():
        cur_trip = child.attrib
        cur_dict = {}
        if cur_trip['id'].find("emergency") != -1:
            cur_dict['id'] = cur_trip['id']
            cur_dict['depart'] = cur_trip['depart']
            cur_dict['arrival'] = cur_trip['arrival']
            cur_dict['duration'] = float(cur_trip['duration'])
            cur_dict['waitingCount'] = cur_trip['waitingCount']
            cur_dict['waitingTime'] = float(cur_trip['waitingTime'])
            ev_trip_data.append(cur_dict)

    return ev_trip_data

def compute_evaluate():
    global range_run
    ev_res = []

    range_run = range(10000, 100001, 10000)

    x = []
    for i in range_run:
        x.append(i)
        ev_trip_data = collect_tripinfo("output", i, "evaluate")
        df = pd.DataFrame(ev_trip_data)

        ev_mean = df["waitingTime"].mean()
        ev_res.append(ev_mean)

        # if ev_mean<35:
        #     print(i)
        #     print(ev_mean)

    plt.ylim(0, 50)

    plt.plot(x, ev_res, c='coral')

    frame = pd.DataFrame({"data": ev_res, "idx": x})
    data_mean = frame.data.values
    plt.plot(frame.idx.values, data_mean, label="Multi Agent", c="#2077b2")
    plt.show()
    print(frame.data.mean())


def plot_flow():
    # flow=np.array([0.4, 0.6, 0.8, 0.9, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2])*250
    # flow=list(flow) + [0] * 3
    # print(len(flow))
    # t = np.arange(0, 3601, 300)
    # plt.step(t, flow, where='post', linewidth=2)
    # plt.xlim([0, 3600])

    flow=np.array([0.8, 1, 0.8])*250
    flow=list(flow) + [0] * 2
    t = np.arange(0, 1201, 400)
    t=list(t)
    t.append(1500)
    print(t)
    print(flow)
    plt.step(t, flow, where='post', linewidth=2)
    plt.xlim([0, 1500])


    plt.xlabel('Simulation time (s)')
    plt.ylabel('Flow rate (veh/hr)')
    plt.grid()
    plt.show()

def plot_trip_ev_waitTime(path,run,mode):
    global range_run
    ev_res = []
    ev_du=[]

    if mode=="train" or mode=="combine_train":
        range_run=range(run)

    elif mode=="test" :
        range_run=range(10,run,10)
    elif mode=="evaluate" :
        range_run = [run]

    x=[]
    for i in range_run:
        x.append(i)
        ev_trip_data=collect_tripinfo(path,i,mode)
        df = pd.DataFrame(ev_trip_data)

        ev_mean = df["waitingTime"].mean()
        ev_res.append(ev_mean)
        ev_du.append(df["duration"].mean())

        # if ev_mean<35:
        #     print(i)
        #     print(ev_mean)

        if mode=="evaluate":
            print(ev_mean)

    #x = range(len(ev_res))
    plt.ylim(0,50)

    plt.plot(x, ev_res)


    frame = pd.DataFrame({"data": ev_res, "idx": x})
    data_mean = frame.data.rolling(30).mean().values

    plt.plot(frame.idx.values, data_mean, label="Independent A2C", c="coral")
    plt.grid()
    plt.show()

    plt.ylim(0,200)

    plt.plot(x, ev_du)
    frame = pd.DataFrame({"data": ev_du, "idx": x})
    data_mean = frame.data.rolling(30).mean().values

    plt.plot(frame.idx.values, data_mean, label="Independent A2C", c="coral")
    plt.grid()
    plt.show()



import os
def plot_judge(run):
    path = '../result_judge/output/judge/'
    df = pd.read_csv(path + ('%s_%s_cover.csv' % ('train', run)))
    plt.plot(df.epoch.values,df.cover.values,label="coverage rate")

    plt.plot(df.epoch.values,df.waste.values,label="waste rate")
    plt.xlabel("Training epoch")
    plt.ylabel("Communication metrics")
    plt.legend()

    plt.grid()
    #plt.show()
    if not os.path.exists('../figures'):
        os.makedirs('../figures')
    plt.savefig('../figures/judge.png')
    print(df)

#plot_judge(399)

#plot_flow()
#compute_priority(1)
plot_trip_ev_waitTime('output',499,"train")
#plot_trip_ev_waitTime('output',90,"evaluate")
#plot_trip_ev_waitTime('output109_priority',1)
#plot_priority_traffic('output109_priority',0)
