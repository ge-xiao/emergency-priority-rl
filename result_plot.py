import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

import xml.etree.cElementTree as ET



# plot 流量设置
# def plot_flow():
#     flow=np.array([0.4, 0.6, 0.8, 0.9, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2])*200
#     print(flow)
#     flow=list(flow) + [0] * 3
#     print(len(flow))
#     t = np.arange(0, 3601, 300)
#     print(len(t))
#     plt.step(t, flow, where='post', linewidth=2)
#     plt.xlim([0, 3600])
#     plt.xlabel('Simulation time (s)')
#     plt.ylabel('Flow rate (veh/hr)')
#     plt.grid()
#     plt.show()


def plot_flow():
    # flow=np.array([0.4, 0.6, 0.8, 0.9, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2])*250
    # flow=list(flow) + [0] * 3
    # print(len(flow))
    # t = np.arange(0, 3601, 300)
    # plt.step(t, flow, where='post', linewidth=2)
    # plt.xlim([0, 3600])

    flow=np.array([0.8, 1, 0.8])*235
    flow=list(flow) + [0] * 2
    t = np.arange(0, 1201, 400)
    t=list(t)
    t.append(1500)
    print(t)
    print(flow)
    plt.step(t, flow,label="flow1",linestyle='-',where='post',alpha=0.6,linewidth=3)

    flow2=np.array([0.5,0.6,0.8,1 ,0.8,0.6])*280
    flow2=list(flow2) + [0] * 2
    t2 = np.arange(0, 1201, 200)
    t2 = list(t2)
    t2.append(1500)

    print(flow2)
    print(t2)

    plt.step(t2, flow2,label="flow2",linestyle='-', where='post',alpha=0.6, linewidth=3)

    plt.xlim([0, 1500])
    #plt.ylim([-30, 300])


    plt.xlabel('Simulation time (s)')
    plt.ylabel('Flow rate (veh/hr)')
    #plt.grid()
    plt.legend()

    plt.show()

def collect_tripinfo(path,run,mode):
    output_path=path+'trip/'
    #print(output_path)
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
            cur_dict['waitingCount'] = float(cur_trip['waitingCount'])
            cur_dict['waitingTime'] = float(cur_trip['waitingTime'])
            cur_dict['timeLoss'] = float(cur_trip['timeLoss'])
            ev_trip_data.append(cur_dict)

    return ev_trip_data


def plot_traffic(run):
    path = '../result/output109/traffic/'
    df = pd.read_csv(path + ('%s_%s_traffic.csv' % ('train', run)))
    avg_queue_mean=df.avg_queue.rolling(60).mean().values
    plt.plot(df.time_sec.values, avg_queue_mean,label="Multi Agent")
    path2= '../result/output109_priority/traffic/'
    priority_df=pd.read_csv(path2+'priority_0_traffic.csv')
    avg_queue_mean_priority=priority_df.avg_queue.rolling(60).mean().values
    plt.plot(priority_df.time_sec.values, avg_queue_mean_priority,c='coral', label="priority strategy")
    plt.xlabel("Simulation time")
    plt.ylabel("Average queue length")
    plt.legend()
    plt.show()


    avg_wait_sec_mean=df.avg_wait_sec.rolling(60).mean().values
    avg_wait_sec_priority=priority_df.avg_wait_sec.rolling(60).mean().values


    plt.plot(df.time_sec.values, avg_wait_sec_mean,label="Multi Agent")
    plt.plot(priority_df.time_sec.values, avg_wait_sec_priority, c='coral', label="priority strategy")
    plt.xlabel("Simulation time")
    plt.ylabel("Average deley (second)")
    plt.legend()
    plt.show()


def plot_double_reward(path1,path2,run):

    df = pd.read_csv(path1 + '/global_reward/'+('train_%s_global_reward.csv' % (run)))
    df = df.drop_duplicates()
    df['avg_reward']=df['avg_reward'].apply(lambda x : 20*x)

    avg_reward_mean=df.avg_reward.rolling(30).mean().values

    plt.plot(df.epoch.values, avg_reward_mean, label="Independent A2C", c="coral")


    df = pd.read_csv(path2 +'/global_reward/'+ ('train_%s_global_reward.csv' % (run)))
    df = df.drop_duplicates()
    df['avg_reward'] = df['avg_reward'].apply(lambda x: 20 * x)

    avg_reward_mean = df.avg_reward.rolling(30).mean().values

    plt.plot(df.epoch.values, avg_reward_mean, label="Multi Agent A2C", c="#2077b2")
    plt.grid()

    plt.xlabel("Training epoch")
    plt.ylabel("global reward")
    plt.ylim(-500, -360)
    plt.legend()
    plt.show()


#对于有无周围状态的结果
def plot_double_result(path1,path2,run):
    ev_res = []

    range_run = range(run)
    x = []
    for i in range_run:
        x.append(i)
        ev_trip_data = collect_tripinfo(path1, i,"train")
        df = pd.DataFrame(ev_trip_data)
        ev_mean = df["waitingTime"].mean()
        ev_res.append(ev_mean)

    # x = range(len(ev_res))
    #plt.plot(x, ev_res, c='coral')
    frame = pd.DataFrame({"data": ev_res, "idx": x})
    data_mean = frame.data.rolling(30).mean().values
    plt.plot(frame.idx.values, data_mean, label="Independent A2C", c="coral")

    ev_res = []

    x = []
    for i in range_run:
        x.append(i)
        ev_trip_data = collect_tripinfo(path2, i,"combine_train")
        df = pd.DataFrame(ev_trip_data)
        ev_mean = df["waitingTime"].mean()
        ev_res.append(ev_mean)
    # x = range(len(ev_res))
    plt.ylim(0,20)
    #plt.plot(x, ev_res, c='coral')
    frame = pd.DataFrame({"data": ev_res, "idx": x})
    data_mean = frame.data.rolling(30).mean().values
    plt.plot(frame.idx.values, data_mean, label="Multi Agent A2C", c="#2077b2")

    plt.xlabel("Training epoch")
    plt.ylabel("EV waiting time")
    plt.legend()
    plt.grid()
    plt.show()



def collect_tripinfo_social(path,run,mode):
    output_path=path+'trip/'
    trip_file = output_path + (mode+'_%s_trip.xml' % (run))
    tree = ET.ElementTree(file=trip_file)

    trip_data=[]
    for child in tree.getroot():
        cur_trip = child.attrib
        cur_dict = {}
        cur_dict['id'] = cur_trip['id']
        cur_dict['depart'] = cur_trip['depart']
        cur_dict['arrival'] = cur_trip['arrival']
        cur_dict['duration'] = float(cur_trip['duration'])
        cur_dict['waitingCount'] = float(cur_trip['waitingCount'])
        cur_dict['waitingTime'] = float(cur_trip['waitingTime'])
        cur_dict['timeLoss'] = float(cur_trip['timeLoss'])
        trip_data.append(cur_dict)

    return trip_data


def compute_evaluate_social(path,mode):
    social_wait_ls = []
    social_duration_ls = []
    social_waitingCount_ls = []
    social_timeLoss_ls = []


    range_run = range(10000, 100001, 10000)
    queue_ls=[]


    x = []
    for i in range_run:
        x.append(i)
        # social_traffic_data = pd.read_csv(path + ("traffic/"+mode+'_%s_traffic.csv' % (i)))
        # queue_mean=social_traffic_data['avg_queue'].mean()
        # queue_ls.append(queue_mean)

        social_trip_data = collect_tripinfo_social(path, i, mode)
        df = pd.DataFrame(social_trip_data)
        social_wait = df["waitingTime"].mean()
        social_duration=df["duration"].mean()
        social_waitingCount=df["waitingCount"].mean()
        social_timeLoss=df["timeLoss"].mean()
        social_wait_ls.append(social_wait)
        social_duration_ls.append(social_duration)
        social_waitingCount_ls.append(social_waitingCount)
        social_timeLoss_ls.append(social_timeLoss)


    frame = pd.DataFrame(
        { "idx": x,"social_wait_ls":social_wait_ls,
          "social_duration_ls":social_duration_ls,"social_waitingCount_ls":social_waitingCount_ls,
          "social_timeLoss_ls":social_timeLoss_ls})

    # print("社会平均排队长度")
    # print(frame.queue_ls.mean())


    output_social={}
    output_social['intersection delay']=str(round(frame.social_wait_ls.mean(),2))+'±'+str(round(frame.social_wait_ls.std(),2))
    output_social['travel time']= str(round(frame.social_duration_ls.mean(),2))+'±'+str(round(frame.social_duration_ls.std(),2))
    output_social['waiting count']=str(round(frame.social_waitingCount_ls.mean(),2))+'±'+str(round(frame.social_waitingCount_ls.std(),2))
    output_social['lost time']= str(round(frame.social_timeLoss_ls.mean(),2))+'±'+str(round(frame.social_timeLoss_ls.std(),2))
    df=[output_social]
    df=pd.DataFrame(df)
    df.to_csv('./result/social.csv',index=False,encoding="utf_8_sig")
    return output_social




def compute_evaluate(path,mode):

    ev_res = []
    ev_duration_ls=[]
    ev_waitingCount_ls=[]
    ev_timeLoss_ls=[]
    range_run = range(10000, 100001, 10000)

    x = []
    for i in range_run:
        x.append(i)
        ev_trip_data = collect_tripinfo(path, i, mode)
        df = pd.DataFrame(ev_trip_data)
        ev_mean = df["waitingTime"].mean()
        ev_duration=df["duration"].mean()
        ev_waitingCount=df["waitingCount"].mean()
        ev_timeLoss=df["timeLoss"].mean()
        ev_res.append(ev_mean)
        ev_duration_ls.append(ev_duration)
        ev_waitingCount_ls.append(ev_waitingCount)
        ev_timeLoss_ls.append(ev_timeLoss)

    #plt.ylim(0, 50)
    #plt.plot(x, ev_res, c='coral')
    frame = pd.DataFrame({"data": ev_res, "idx": x,"ev_duration_ls":ev_duration_ls,"ev_waitingCount_ls":ev_waitingCount_ls,"ev_timeLoss_ls":ev_timeLoss_ls})
    #data_mean = frame.data.values
    #plt.plot(frame.idx.values, data_mean, label="Multi Agent", c="#2077b2")
    #plt.show()

    output_ev={}
    output_ev['intersection delay']=str(round(frame.data.mean(),2))+'±'+str(round(frame.data.std(),2))
    output_ev['travel time']=str(round(frame.ev_duration_ls.mean(),2))+'±'+str(round(frame.ev_duration_ls.std(),2))
    output_ev['waiting count']=str(round(frame.ev_waitingCount_ls.mean(),2))+'±'+str(round(frame.ev_waitingCount_ls.std(),2))
    output_ev['lost time']=str(round(frame.ev_timeLoss_ls.mean(),2))+'±'+str(round(frame.ev_timeLoss_ls.std(),2))

    df=[output_ev]
    df=pd.DataFrame(df)
    df.to_csv('./result/ev.csv',index=False,encoding="utf_8_sig")
    return output_ev

def compute_evaluate_judge(path,mode):
    range_run = range(10000, 100001, 10000)

    x = []
    cover_ls=[]
    waste_ls=[]
    for i in range_run:
        x.append(i)

        data = pd.read_csv(path+'judge/'+('combine_evaluate_%s_cover.csv' % (i)))

        cover_ls.append(data.cover.mean())
        waste_ls.append(data.waste.mean())
    output_ev={}
    output_ev['cover']=np.array(cover_ls).mean()
    output_ev['waste']=np.array(waste_ls).mean()

    df=[output_ev]
    df=pd.DataFrame(df)
    df.to_csv('./result/judge.csv',index=False,encoding="utf_8_sig")




plot_flow()
compute_evaluate_judge("./result/output/","combine_evaluate")
compute_evaluate("./result/output/","combine_evaluate_1")
compute_evaluate_social("./result/output/","combine_evaluate_1")

#compute_evaluate("./result/output_priority/","evaluate")
#compute_evaluate_social("./result/output_priority/","evaluate")

