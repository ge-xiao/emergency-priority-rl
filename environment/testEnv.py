import configparser
from environment.new_env import TrafficSimulator
#from environment.EMVLight_env import TrafficSimulator

import numpy as np


if __name__ == '__main__':
    config = configparser.ConfigParser()
    #config.read('../config/test_3x3_moreReal.ini')
    config.read('../config/test_5x5/judge.ini')
    #config.read('../config/test_5x5/EMVLight.ini')


    env=TrafficSimulator(config['ENV_CONFIG'])

    step=0

    obs = env.reset()
    print(len(obs[0]))

    while True:


        actions = []
        for node_name in env.sorted_nodes:
            #actions.append(self.greedy(ob, node_name))
            actions.append(np.random.choice([0,1, 2, 3,4,5,6,7]))
            #actions.append(2)
        next_ob, reward, done, global_reward = env.step(actions)
        #print(next_ob[0])

        if done:
            break

        step+=1


        ob = next_ob
