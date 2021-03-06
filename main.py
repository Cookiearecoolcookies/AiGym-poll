import random

import gym

import numpy as np
import pkg_resources
pkg_resources.require("tensorflow==1.8.0")
import tensorflow as tf
from collections import deque

env = gym.make('CartPole-v0')
state = env.reset()

# State:
# ### Observation Space
# The observation is a `ndarray` with shape `(4,)` where the elements correspond to the following:
#     | Num | Observation           | Min                  | Max                |
# |-----|-----------------------|----------------------|--------------------|
# | 0   | Cart Position         | -4.8*                 | 4.8*                |
# | 1   | Cart Velocity         | -Inf                 | Inf                |
# | 2   | Pole Angle            | ~ -0.418 rad (-24°)** | ~ 0.418 rad (24°)** |
# | 3   | Pole Angular Velocity | -Inf                 | Inf                |

# https://en.wikipedia.org/wiki/Bellman_equation


class QNetwork():
    def __init__(self, state_dim, action_size):
        tf.reset_default_graph()
        self.state_in = tf.placeholder(tf.float32, shape=[None, *state_dim])
        self.action_in = tf.placeholder(tf.int32, shape=[None])
        self.q_target_in = tf.placeholder(tf.float32, shape=[None])
        self.importance_in = tf.placeholder(tf.float32, shape=[None])
        action_one_hot = tf.one_hot(self.action_in, depth=action_size)

        self.hidden1 = tf.layers.dense(self.state_in, 100, activation=tf.nn.relu)
        self.q_state = tf.layers.dense(self.hidden1, action_size, activation=None)

        self.q_state_action = tf.reduce_sum(tf.multiply(self.q_state, action_one_hot), axis=1)

        self.loss = tf.reduce_mean(tf.square(self.q_state_action - self.q_target_in))
        self.optimizer = tf.train.AdamOptimizer(learning_rate=0.001).minimize(self.loss)

    def get_q_state(self, session, state):
        q_state = session.run(self.q_state, feed_dict={self.state_in: state})
        return q_state

    def update_model(self, session, state, action, q_target):
        feed = {self.state_in: state, self.action_in: action, self.q_target_in: q_target}
        session.run(self.optimizer, feed_dict=feed)

class ReplayBuffer():
    def __init__(self, maxlen):
        self.buffer = deque(maxlen=maxlen)

    def add(self, experience):
        self.buffer.append(experience)

    def sample(self, batch_size):
        sample_size = min(len(self.buffer), batch_size)
        samples = random.choices(self.buffer, k=sample_size)
        return map(list, zip(*samples))

class Agent():
    def __init__(self, env):
        self.state_dim = env.observation_space.shape
        self.action_size = env.action_space.n
        self.q_network = QNetwork(self.state_dim, self.action_size)
        self.eps =1.0
        self.replay_buffer = ReplayBuffer(maxlen=10000)

        self.sess = tf.Session()
        self.sess.run(tf.global_variables_initializer())

    def get_action(self, state):
        q_state = self.q_network.get_q_state(self.sess,[state])
        greedy_action = np.argmax(q_state)
        action_random =  np.random.randint(self.action_size)
        action = action_random if random.random() < self.eps else greedy_action
        return action

    def train(self, state, action, next_state, reward, done):
        self.replay_buffer.add((state, action, next_state, reward, done))
        states, actions,  next_states, rewards, dones = self.replay_buffer.sample(50)
        q_next_states = self.q_network.get_q_state(self.sess, next_states)
        q_next_states[dones] = np.zeros([self.action_size])
        q_targets = rewards + 0.99 * np.max(q_next_states, axis=1)
        self.q_network.update_model(self.sess, states, actions, q_targets)

        if done:
            self.eps = max(1.0, 0.1 * self.eps)

    def __del__(self):
        self.sess.close()

agent = Agent(env)

for ep in range(500):
    state = env.reset()
    total_reward = 0
    done = False
    while not done:
        action = agent.get_action(state)
        next_state, reward, done, info = env.step(action)
        agent.train(state, action, next_state, reward, done)
        env.render()
        total_reward+=reward
        state = next_state

    print("ep {}, total_reward: {:.2f}".format(ep,total_reward))

env.close()
