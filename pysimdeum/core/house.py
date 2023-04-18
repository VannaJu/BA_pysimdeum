import numpy as np
import pandas as pd
import xarray as xr
import pickle
from datetime import datetime
from typing import Any, Union
from pysimdeum.core.utils import Base, chooser, normalize
from pysimdeum.core.statistics import Statistics
from pysimdeum.core.user import User
import pysimdeum.core.end_use as EndUses
from dataclasses import dataclass, field

# TODO: Implement multiple appliances which will be later on divided over the users, so they are not blocked
# TODO: Link data to OOPNET
# TODO: Increase speed of program
# TODO: Documentation
# TODO: Think about if Property class is necessary or if it can be integrated into the House class


@dataclass
class Property(Base):
    """Property represents a parcel of land on which a house is/can be build.

    Additionally, it contains information on statistics, and the location of the house, plus a connection to the oopnet_id
    """

    house_type: str = ""
    _house: Any = None
    statistics: Statistics = None
    country: str = "NL"

    # TODO: implement following quantities
    oopnet_id: str = ""
    lattitude: float = np.nan
    longitude: float = np.nan
    x_coordinate: float = np.nan
    y_coordinate: float = np.nan
    
    random_state: int = None # Change: Random Seeds


    def __post__init__(self):
        if Statistics is None:
            self.statistics = Statistics(country=self.country)


    def _choose_type(self, statistics: Statistics=None) -> str:

        if not statistics:
            raise Exception('Statistics object has to be defined')
        else:
            self.house_type = chooser(data=statistics.household, myproperty='households', random_state = self.random_state)  # Change: Random Seeds 

        return self.house_type

    def built_house(self, house_type: str="", housefile: str="", random_state: int = None): # Change: Random Seeds
        
        """
        house_type: own_person, one_person, two_person, family
        housefile: to upload existing house file        
        random_state: for chooser house_type, user gender and job and family household size # TODO
        """
    
        # TODO: House chooser seems not to work if API:built_house does not specify a house_type

        if housefile:
            with open(housefile, 'rb') as f:
                new_house = pickle.load(f)
            self.house = new_house
            
        else:
            
            self.random_state = random_state   # Change: Random Seeds 
        
            if house_type:
                self.house_type = house_type
            else:
                self._choose_type(self.statistics)
            self.house = House(id=self.id,
                            house_type=self.house_type,
                            statistics=self.statistics,
                            oopnet_id=self.oopnet_id,
                            lattitude=self.lattitude,
                            longitude=self.longitude,
                            x_coordinate=self.x_coordinate,
                            y_coordinate=self.y_coordinate,
                            random_state = self.random_state)  # Change: Random Seeds 

        return self.house


@dataclass
class House(Property):
    """pysimdeum House containting information on users, appliances and consumption.

    This class is a child of the `Property` class. It containts methods for populating and furnishing a house, and 
    methods to initialise and run simulations.
    """

    users: list = field(default_factory=list)  # List of users/inhabitants present in the house
    appliances: list = field(default_factory=list)  # List of appliances/water end-use devices in the house
    consumption: xr.DataArray = field(default_factory=xr.DataArray)  # property to store the consumption of a house

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}:\n\tid\t=\t{self.id}\n\ttype\t=' \
               f'\t{self.house_type}\n\tuser\t=\t{len(self.users)}\n' \
               f'\tappliances\t=\t{list(map(lambda x: x.__class__.__name__, self.appliances))}'
    
    def __str__(self):
        return self.__repr__()

    def populate_house(self, users: [] = [], random_state_user: [] = None) -> None: # Change: Random Seeds and input users
        """
        
        users: list of given user, the house_type needs to be 'own_person'
               User can be given as a dict or a tuple
               as dict the keywords are age, gender, and job 
               as tuple the order has to be: gender, age and job 
        
        random_state_user: one random_state for each user to select age of user
        
        """

        # job statistic
        job_stats = normalize(pd.Series(self.statistics.household[self.house_type]['job']))

        # division age statistics
        age_stats = normalize(pd.Series(self.statistics.household[self.house_type]['division_age']))

        # division gender statistics
        gender_stats = normalize(pd.Series(self.statistics.household[self.house_type]['division_gender']))
        
        if self.house_type == 'own_person': # Change: Input Users as own type of house 
            
            if len(users) != 0:
                for (i , user)  in enumerate(users): 
                    if isinstance(user, dict):
                        self.users.append(User(id = 'user_' + str(i), age = user['age'], gender = user['gender'], job = user['job']))
                    elif isinstance(user, tuple):
                        self.users.append(User(id = 'user_' + str(i), gender = user[0], age = user[1], job = user[2] ))
        
        elif self.house_type == 'one_person':
            
            if isinstance(random_state_user, list):
                random_state_user = random_state_user[0]

            age = chooser(data=age_stats, random_state = random_state_user) # Change: Random Seeds 
            gender = chooser(data=gender_stats, random_state = random_state_user) # Change: Random Seeds 
            job = False

            if age == 'adult':
                u = np.random.RandomState(seed = random_state_user).uniform()
                if u < job_stats[gender]:
                    job = True

            self.users = [User(id='user_1', age=age, gender=gender, job=job)]

        elif self.house_type == 'two_person':
            # todo: implement same sex households
            
            # Change: Random Seeds
            if random_state_user != None and len(random_state_user) == 2:
                random_state_user_1 = random_state_user[0] 
                random_state_user_2 = random_state_user[1]
            else:    
                random_state_user_1 = None
                random_state_user_2 = None
            
            # choose age
            age1 = chooser(data=age_stats, random_state = random_state_user_1) # Change: Random Seeds  
            age2 = chooser(data=age_stats, random_state = random_state_user_2) # Change: Random Seeds 

            # choose gender
            gender = chooser(data=gender_stats, random_state = self.random_state) # Change: Random Seeds 
            gender1, gender2 = gender.split('_')

            # choose job
            job1 = False
            job2 = False
            u = np.random.RandomState(seed = self.random_state).uniform() # Change: Random Seeds 

            # have a job
            if age1 == 'senior':
                if age2 == 'adult':
                    if u < job_stats['only_female'] / (job_stats['only_female'] + job_stats['neither_person']):
                        job2 = True

            if age2 == 'senior':
                if age1 == 'adult':
                    if u < job_stats['only_male'] / (job_stats['only_male'] + job_stats['neither_person']):
                        job1 = True

            if (age1 == 'adult') and (age2 == 'adult'):
                job = chooser(job_stats, random_state = self.random_state) # Change: Random Seeds 
                if job == 'both': 
                    job1 = True
                    job2 = True
                elif job == 'only_male':
                    job1 = True
                    job2 = False
                elif job == 'only_female':
                    job1 = False
                    job2 = True
                elif job == 'neither_person':
                    job1 = False
                    job2 = False
                else:
                    raise Exception('Unknown job attribute, not implemented.')

            self.users = [User(id='user_1', age=age1, gender=gender1, job=job1),
                          User(id='user_2', age=age2, gender=gender2, job=job2)]

        elif self.house_type == 'family':

            averagenumpeople = self.statistics.household[self.house_type]['people']
            minnum = 2
            maxnum = 5
            rNum = np.random.RandomState(seed = self.random_state).binomial(n=maxnum - minnum, p=(averagenumpeople - minnum) / (maxnum - minnum)) + minnum # Change: Random Seeds 

            if rNum == 2:  # mother and child/teen

                u = np.random.RandomState(seed = self.random_state).uniform() # Change: Random Seeds 

                # mother
                job = False
                if u < job_stats[['both', 'only_female']].sum():  # not correct, this is for two partners (comment
                    # from Mirjam Blokker)
                    job = True
                mother = User(id='user_1', age='adult', job=job, gender='female')

                # child
                gender = chooser(gender_stats, random_state = self.random_state) # Change: Random Seeds 
                age = chooser(age_stats[['child', 'teen']], random_state = self.random_state) # Change: Random Seeds 
                child = User(id='user_2', age=age, job=False, gender=gender)

                self.users = [mother, child]

            elif rNum in [3, 4, 5]:

                # Generate parents 
                job = chooser(job_stats, random_state = self.random_state) # Change: Random Seeds 
                if job == 'both':
                    f_job = True
                    m_job = True
                elif job == 'only_male':
                    f_job = True
                    m_job = False
                elif job == 'only_female':
                    f_job = False
                    m_job = True
                elif job == 'neither_person':
                    f_job = False
                    m_job = False

                family = [User(id='user_1', gender='male', age='adult', job=f_job),  # father
                          User(id='user_2', gender='female', age='adult', job=m_job)]  # mother

                # add child/teen until family size is reached
                for numchild in range(2, rNum):
                    rnd_state = self.random_state if self.random_state is None else self.random_state+numchild # Change: Random Seeds 
                    gender = chooser(gender_stats, random_state = rnd_state) # Change: Random Seeds 
                    age = chooser(age_stats[['child', 'teen']], random_state = self.random_state) # Change: Random Seeds 
                    family += [User(id='user_' + str(numchild+1), gender=gender, age=age, job=False)]  
                    # additional
                    # child

                self.users = family

            else:
                raise Exception('Family size exceeded!')
        else:

            raise NotImplementedError('Household type is not implemented')
    
    # Change: Add explicit User(s) after creation of house 
    def add_user(self, users): 
        """
        users: user(s) to add
               can be a single tuple or dict or a list of tuple or dict
        """
                                          
        if self.house_type == 'own_person':
            if isinstance(users, dict) or isinstance(users, tupel):
                users = [users]
            for (i , user)  in enumerate(users): 
                if isinstance(user, dict):
                    self.users.append(User(id = 'user_' + str(i+len(self.users)), age = user['age'], gender = user['gender'], job = user['job']))
                elif isinstance(user, tuple):
                    self.users.append(User(id = 'user_' + str(i+len(self.users)), gender = user[0], age = user[1], job = user[2] ))                                  

    def furnish_house(self, furnish: [] = [], random_state_furnish: [] = None): # Change: Random Seeds 
        """
        furnish: string of the exact furnish to add
        random_state_furnish: random state for each furnish to get selected 
        """
        
        # Change: Random Seeds
        if random_state_furnish is None:
            random_state_furnish = [None] * len(self.statistics.end_uses.items()) 
        
        # Change: Input furnish   
        if len(furnish) > 0:
            for furn in furnish:
                classname = furn
                if 'Shower' in furn:
                    classname = 'Shower'
                elif 'Wc' in furn:
                    classname = 'Wc'
                
                appliance = self.statistics.end_uses[classname]
                eu_instance = getattr(EndUses, furn)(statistics=appliance)
                self.appliances.append(eu_instance)
                    
        else:
            for i, ( key, appliances ) in enumerate(self.statistics.end_uses.items()):

                penetration = appliances['penetration']
                classname = appliances['classname']
                inhabitants = str(len(self.users))

                u = np.random.RandomState(seed = random_state_furnish[i]).uniform() * 100 # Change: Random Seeds 
                #u = np.random.RandomState(seed = self.random_state).uniform() * 100  # probability in percent

                # penetration dependent on number of inhabitants
                if isinstance(penetration, dict):
                    penetration = penetration[inhabitants]

                if u <= penetration:
                    if classname == 'Shower':
                        showertype = chooser(appliances['subtype'], 'penetration', random_state = self.random_state) # Change: Random Seeds 
                        eu_instance = getattr(EndUses, showertype)(statistics=appliances) 
                    elif classname == 'Wc':
                        wctype = chooser(appliances['subtype'], 'penetration', random_state = self.random_state) # Change: Random Seeds 
                        eu_instance = getattr(EndUses, wctype)(statistics=appliances)
                    else:
                        eu_instance = getattr(EndUses, classname)(statistics=appliances)
                    self.appliances.append(eu_instance)
     
    # Change: Add furnishs after creation of house 
    def add_furnish(self, furnish):
        """
            furnish: can be a list of enduses or a single enduse
        """
        
        if isinstance(furnish, str):
            furnish = [furnish]
        
        for furn in furnish:
            classname = furn
            if 'Shower' in furn:
                classname = 'Shower'
            elif 'Wc' in furn:
                classname = 'Wc'

            appliance = self.statistics.end_uses[classname]
            eu_instance = getattr(EndUses, furn)(statistics=appliance)
            self.appliances.append(eu_instance)

    def simulate(self, date=None, duration='1 day', num_patterns=1, random_state_enduse: [] = None, random_state_user_day: [] = None ): # Change: Random Seeds 
        """
        
        duration: in days 
        num_patterns: removeable?, optional
        random_state_enduse: list of random_states for each enduse, optional  
        random_state_user_day: list of list, for each user for each day, optional
        
        """
        
        if date is None:
            date = datetime.now().date()
        try:
            timedelta = pd.to_timedelta(duration)
        except:
            print('Warning: duration unrecognized defaulted to 1 day')
            timedelta = pd.to_timedelta('1 day')
        # time = pd.timedelta_range(start='00:00:00', end='24:00:00', freq='1s', closed='left')
        # time = pd.date_range(start=date, end=date + timedelta, freq='1s', closed='left')
        time = pd.date_range(start=date, end=date + timedelta, freq='1s')
        users = [x.id for x in self.users] + ['household']
        enduse = [x.statistics['classname'] for x in self.appliances]
        patterns = [x for x in range(0, num_patterns)]
        consumption = np.zeros((len(time), len(users), len(enduse), num_patterns))
        
        # Change: Random Seeds 
        if random_state_user_day is None:
            random_state_user_day = [None] * len(self.users)
        
        # Change: Fix duration 
        for u, user in enumerate(self.users):
            user.compute_presence(statistics=self.statistics, duration = duration, random_state = random_state_user_day[u])
        
        days = pd.date_range(start=date, end=date + timedelta - pd.to_timedelta('1 d'), freq = '1d') # Change: Fix duration 
        
         # Change: Random Seeds 
        if random_state_enduse is None:
            random_state_enduse = np.full((len(days), len(self.appliances)), None)
       
        # Change: Fix duration 
        for d, day in enumerate(days):
            
            day_begin = d * 86400   # Change: Fix duration 
            day_end = (d+1) * 86400 # Change: Fix duration 
            
            for num in patterns:
                for k, appliance in enumerate(self.appliances):

                    consumption = appliance.simulate(consumption, users=self.users, ind_enduse=k, pattern_num=num, day_begin = day_begin, day_end = day_end, random_state = random_state_enduse[d][k])  # Change: Random Seeds, Fix Duration
        
            self.consumption = xr.DataArray(data=consumption, coords=[time, users, enduse, patterns], dims=['time', 'user', 'enduse', 'patterns'])

        return self.consumption

    def save_house(self, outputname):
        """
        TODO 
        """
        
#        if self.consumption == None: #only save simulated houses
#            self.simulate()
        with open(outputname + '.house', 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
    
        
# this class is introduced for storage purposes. 
# It is meant for those cases where only demand data per house is needed 
# and not the individual data of the users and or appliances
# the conumption datarray therefore only contains totals
# user and appliance data is removed for now
@dataclass
class HousePattern:

    house: Union[House, str]
    users: list = field(default_factory=list, init=False)
    appliances: list = field(default_factory=list, init=False)
    consumption: list = field(default_factory=list, init=False)

    def __post__init__(self, house):

        if type(self.house) == House:
            self.users = self.house.users
            self.appliances = self.house.appliances 
            self.consumption = self.house.consumption.sum('user').sum('enduse')
        
        elif type(self.house) == str:
            with open(house, 'rb') as f:
                new_house_pattern = pickle.load(f)
                self.users = new_house_pattern.users
                self.appliances = new_house_pattern.appliances
                self.consumption = new_house_pattern.consumption
   
    def save_house_pattern(self, outputname):
        with open(outputname + '.housepattern', 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
    