from pysimdeum.core.statistics import Statistics
from pysimdeum.core.house import Property, HousePattern, House

# Change: Random Seeds and housefile
def built_house(housefile: str = "", house_type: str = "", users: [] = [], furnish: [] = [], random_state_house: int = None, random_state_user: [] = None, random_state_furnish: [] = None ) -> House:

    stats = Statistics()
    prop = Property(statistics=stats)
    
    # Change: Load given House-file 
    if housefile:
        house = prop.built_house(housefile = housefile)
    else:
        # Change: Remove creation of users presence and simulation of house   
        house = prop.built_house(house_type=house_type, random_state = random_state_house)
        house.populate_house(users = users, random_state_user = random_state_user)
        house.furnish_house(furnish = furnish, random_state_furnish = random_state_furnish)

    return house
