import gym
from gym import spaces
import numpy as np

class ChatbotEnv(gym.Env):
    def __init__(self, tags, input_size):
        super(ChatbotEnv, self).__init__()
        # Définition des espaces d'action et d'observation
        self.action_space = spaces.Discrete(len(tags))  # Nombre d'actions possibles (tags)
        self.observation_space = spaces.Box(low=0, high=1, shape=(input_size,), dtype=np.float32)
        # État initial
        self.state = np.zeros(input_size, dtype=np.float32)
        
    def reset(self):
        # Réinitialiser l'état de l'environnement
        self.state = np.zeros(self.observation_space.shape, dtype=np.float32)
        return self.state
    
    def step(self, action):
        reward = self._compute_reward(action)
        done = False 
        info = {}
        # Mettre à jour l'état si nécessaire
        self.state = np.zeros(self.observation_space.shape, dtype=np.float32)
        return self.state, reward, done, info
    
    def _compute_reward(self, action):
        # Calculer la récompense (par exemple, en fonction du feedback utilisateur)
        return np.random.rand()
