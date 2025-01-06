import os
import csv
import random
import matplotlib.pyplot as plt
import numpy as np

def get_votes_by_party(directory, bill=None):
    if bill is None:
        # Get all the file paths in the directory
        file_paths = []
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_paths.append(file_path)
        
        # Get the votes for each bill
        Party_Votes = []
        for file_path in file_paths:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                reader = csv.reader(file)
                # Skip the header row
                header = next(reader)

                voters = list(reader)
                # print(f"Number of voters: {len(voters)}")
                # Prints name of Parliament session
                # print(f"Parliament: {directory}")
                # Prints name of file
                # print(f"Bill: {file_path}")

                # Count the number of votes by party and return them as lists
                Conservative_Votes = []
                Liberal_Votes = []
                NDP_Votes = []
                Bloc_Votes = []
                Green_Votes = []
                Independent_Votes = []

                try:
                    for voter in voters:
                        if voter[1] == "Conservative":
                            Conservative_Votes.append((voter[0], voter[2]))
                        elif voter[1] == "Liberal":
                            Liberal_Votes.append((voter[0], voter[2]))
                        elif voter[1] == "NDP":
                            NDP_Votes.append((voter[0], voter[2]))
                        elif voter[1] == "Bloc Québécois":
                            Bloc_Votes.append((voter[0], voter[2]))
                        elif voter[1] == "Green":
                            Green_Votes.append((voter[0], voter[2]))
                        else:
                            Independent_Votes.append((voter[0], voter[2]))
                except IndexError:
                    pass

                filename = os.path.basename(file_path)[:-4]
                Party_Votes.append([Conservative_Votes, Liberal_Votes, NDP_Votes, Bloc_Votes, Green_Votes, Independent_Votes, filename])
        
        return Party_Votes

    else:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)        
            if os.path.isfile(file_path) and bill in file_path:
                with open(file_path, 'r') as file:
                    reader = csv.reader(file)
                    # Skip the header row
                    header = next(reader)

                    voters = list(reader)
                    print(f"Number of voters: {len(voters)}")
                    # Prints name of Parliament session
                    print(f"Parliament: {directory}")
                    # Prints name of file
                    print(f"Bill: {filename}")

                    # Count the number of votes by party and return them as lists
                    Conservative_Votes = []
                    Liberal_Votes = []
                    NDP_Votes = []
                    Bloc_Votes = []
                    Green_Votes = []
                    Independent_Votes = []

                    try:
                        for voter in voters:
                            if voter[1] == "Conservative":
                                Conservative_Votes.append((voter[0], voter[2]))
                            elif voter[1] == "Liberal":
                                Liberal_Votes.append((voter[0], voter[2]))
                            elif voter[1] == "NDP":
                                NDP_Votes.append((voter[0], voter[2]))
                            elif voter[1] == "Bloc Québécois":
                                Bloc_Votes.append((voter[0], voter[2]))
                            elif voter[1] == "Green":
                                Green_Votes.append((voter[0], voter[2]))
                            else:
                                Independent_Votes.append((voter[0], voter[2]))
                    except IndexError:
                        Party_Votes = [Conservative_Votes, Liberal_Votes, NDP_Votes, Bloc_Votes, Green_Votes, Independent_Votes]


                    Party_Votes = [Conservative_Votes, Liberal_Votes, NDP_Votes, Bloc_Votes, Green_Votes, Independent_Votes]

        return Party_Votes

def display_cohesion_by_party(party_votes):
    if len(party_votes) > 6:
        # There are multiple bills, so we're going to calculate the cohesion for each bill and
        # then average the cohesion for each party across all bills

        Party_Cohesion = []

        for bill_votes in party_votes:
            Conservative_Party_Size = len(bill_votes[0])
            Liberal_Party_Size = len(bill_votes[1])
            NDP_Party_Size = len(bill_votes[2])
            Bloc_Party_Size = len(bill_votes[3])
            Green_Party_Size = len(bill_votes[4])
            Independent_Party_Size = len(bill_votes[5])

            # Conservative Cohesion
            try:
                Conservative_yea_votes = 0
                Conservative_nay_votes = 0
                for vote in bill_votes[0]:
                    if vote[1] == "Yea":
                        Conservative_yea_votes += 1
                    elif vote[1] == "Nay":
                        Conservative_nay_votes += 1
                    else:
                        Conservative_Party_Size -= 1
                
                if Conservative_yea_votes >= Conservative_nay_votes:
                    Conservative_Cohesion = round(Conservative_yea_votes / Conservative_Party_Size * 100, 2)
                else:
                    Conservative_Cohesion = round(Conservative_nay_votes / Conservative_Party_Size * 100, 2)
            except ZeroDivisionError:
                Conservative_Cohesion = None
            
            # Liberal Cohesion
            try:
                Liberal_yea_votes = 0
                Liberal_nay_votes = 0
                for vote in bill_votes[1]:
                    if vote[1] == "Yea":
                        Liberal_yea_votes += 1
                    elif vote[1] == "Nay":
                        Liberal_nay_votes += 1
                    else:
                        Liberal_Party_Size -= 1
                
                if Liberal_yea_votes >= Liberal_nay_votes:
                    Liberal_Cohesion = round(Liberal_yea_votes / Liberal_Party_Size * 100, 2)
                else:
                    Liberal_Cohesion = round(Liberal_nay_votes / Liberal_Party_Size * 100, 2)
            except ZeroDivisionError:
                Liberal_Cohesion = None
            
            # NDP Cohesion
            try:
                NDP_yea_votes = 0
                NDP_nay_votes = 0
                for vote in bill_votes[2]:
                    if vote[1] == "Yea":
                        NDP_yea_votes += 1
                    elif vote[1] == "Nay":
                        NDP_nay_votes += 1
                    else:
                        NDP_Party_Size -= 1
                
                if NDP_yea_votes >= NDP_nay_votes:
                    NDP_Cohesion = round(NDP_yea_votes / NDP_Party_Size * 100, 2)
                else:
                    NDP_Cohesion = round(NDP_nay_votes / NDP_Party_Size * 100, 2)
            except ZeroDivisionError:
                NDP_Cohesion = 1
            
            # Bloc Cohesion
            try:
                Bloc_yea_votes = 0
                Bloc_nay_votes = 0
                for vote in bill_votes[3]:
                    if vote[1] == "Yea":
                        Bloc_yea_votes += 1
                    elif vote[1] == "Nay":
                        Bloc_nay_votes += 1
                    else:
                        Bloc_Party_Size -= 1
                
                if Bloc_yea_votes >= Bloc_nay_votes:
                    Bloc_Cohesion = round(Bloc_yea_votes / Bloc_Party_Size * 100, 2)
                else:
                    Bloc_Cohesion = round(Bloc_nay_votes / Bloc_Party_Size * 100, 2)
            except ZeroDivisionError:
                Bloc_Cohesion = None
            
            # Green Cohesion
            try:
                Green_yea_votes = 0
                Green_nay_votes = 0
                for vote in bill_votes[4]:
                    if vote[1] == "Yea":
                        Green_yea_votes += 1
                    elif vote[1] == "Nay":
                        Green_nay_votes += 1
                    else:
                        Green_Party_Size -= 1
                
                if Green_yea_votes >= Green_nay_votes:
                    Green_Cohesion = round(Green_yea_votes / Green_Party_Size * 100, 2)
                else:
                    Green_Cohesion = round(Green_nay_votes / Green_Party_Size * 100, 2)
            except ZeroDivisionError:
                Green_Cohesion = None
            
            # Independent Cohesion
            try:
                Independent_yea_votes = 0
                Independent_nay_votes = 0
                for vote in bill_votes[5]:
                    if vote[1] == "Yea":
                        Independent_yea_votes += 1
                    elif vote[1] == "Nay":
                        Independent_nay_votes += 1
                    else:
                        Independent_Party_Size -= 1

                if Independent_yea_votes >= Independent_nay_votes:
                    Independent_Cohesion = round(Independent_yea_votes / Independent_Party_Size * 100, 2)
                else:
                    Independent_Cohesion = round(Independent_nay_votes / Independent_Party_Size * 100, 2)
            except ZeroDivisionError:
                Independent_Cohesion = None
            
            Party_Cohesion.append([(Conservative_Cohesion, Conservative_Party_Size, Conservative_yea_votes, Conservative_nay_votes), (Liberal_Cohesion, Liberal_Party_Size, Liberal_yea_votes, Liberal_nay_votes), (NDP_Cohesion, NDP_Party_Size, NDP_yea_votes, NDP_nay_votes), (Bloc_Cohesion, Bloc_Party_Size, Bloc_yea_votes, Bloc_nay_votes), (Green_Cohesion, Green_Party_Size, Green_yea_votes, Green_nay_votes), (Independent_Cohesion, Independent_Party_Size, Independent_yea_votes, Independent_nay_votes)])
         
        # Calculate the average cohesion for each party across all bills
        Conservative_Cohesion = 0
        Liberal_Cohesion = 0
        NDP_Cohesion = 0
        Bloc_Cohesion = 0
        Green_Cohesion = 0
        Independent_Cohesion = 0

        ## HOW CAN I EXCLUDE THE N/A VALUES FROM THE AVERAGE?
        

        for cohesion in Party_Cohesion:
            Conservative_Cohesion += cohesion[0][0]
            Liberal_Cohesion += cohesion[1][0]
            NDP_Cohesion += cohesion[2][0]
            Bloc_Cohesion += cohesion[3][0]
            Green_Cohesion += cohesion[4][0]
            Independent_Cohesion += cohesion[5][0]
        
        Conservative_Cohesion = round(Conservative_Cohesion / len(Party_Cohesion), 2)
        Liberal_Cohesion = round(Liberal_Cohesion / len(Party_Cohesion), 2)
        NDP_Cohesion = round(NDP_Cohesion / len(Party_Cohesion), 2)
        Bloc_Cohesion = round(Bloc_Cohesion / len(Party_Cohesion), 2)
        Green_Cohesion = round(Green_Cohesion / len(Party_Cohesion), 2)
        Independent_Cohesion = round(Independent_Cohesion / len(Party_Cohesion), 2)
        
        Party_Cohesion = [Conservative_Cohesion, Liberal_Cohesion, NDP_Cohesion, Bloc_Cohesion, Green_Cohesion, Independent_Cohesion]
    
        return Party_Cohesion
    
    else:
        
        # There is only one bill, so we're going to calculate the cohesion for this bill

        # Party cohesion is defined as the percentage of votes that are the same as the party's majority vote
        Conservative_Party_Size = len(party_votes[0])
        Liberal_Party_Size = len(party_votes[1])
        NDP_Party_Size = len(party_votes[2])
        Bloc_Party_Size = len(party_votes[3])
        Green_Party_Size = len(party_votes[4])
        Independent_Party_Size = len(party_votes[5])

        # Conservative Cohesion
        try:
            Conservative_yea_votes = 0
            Conservative_nay_votes = 0
            for vote in party_votes[0]:
                if vote[1] == "Yea":
                    Conservative_yea_votes += 1
                elif vote[1] == "Nay":
                    Conservative_nay_votes += 1
                else:
                    Conservative_Party_Size -= 1
            
            if Conservative_yea_votes >= Conservative_nay_votes:
                Conservative_Cohesion = round(Conservative_yea_votes / Conservative_Party_Size * 100, 2)
            else:
                Conservative_Cohesion = round(Conservative_nay_votes / Conservative_Party_Size * 100, 2)
        except ZeroDivisionError:
            Conservative_Cohesion = None

        # Liberal Cohesion
        try:
            Liberal_yea_votes = 0
            Liberal_nay_votes = 0
            for vote in party_votes[1]:
                if vote[1] == "Yea":
                    Liberal_yea_votes += 1
                elif vote[1] == "Nay":
                    Liberal_nay_votes += 1
                else:
                    Liberal_Party_Size -= 1
            
            if Liberal_yea_votes >= Liberal_nay_votes:
                Liberal_Cohesion = round(Liberal_yea_votes / Liberal_Party_Size * 100, 2)
            else:
                Liberal_Cohesion = round(Liberal_nay_votes / Liberal_Party_Size * 100, 2)
        except ZeroDivisionError:
            Liberal_Cohesion = None
        
        # NDP Cohesion
        try:
            NDP_yea_votes = 0
            NDP_nay_votes = 0
            for vote in party_votes[2]:
                if vote[1] == "Yea":
                    NDP_yea_votes += 1
                elif vote[1] == "Nay":
                    NDP_nay_votes += 1
                else:
                    NDP_Party_Size -= 1
            
            if NDP_yea_votes >= NDP_nay_votes:
                NDP_Cohesion = round(NDP_yea_votes / NDP_Party_Size * 100, 2)
            else:
                NDP_Cohesion = round(NDP_nay_votes / NDP_Party_Size * 100, 2)
        except ZeroDivisionError:
            NDP_Cohesion = None
        
        # Bloc Cohesion
        try:
            Bloc_yea_votes = 0
            Bloc_nay_votes = 0
            for vote in party_votes[3]:
                if vote[1] == "Yea":
                    Bloc_yea_votes += 1
                elif vote[1] == "Nay":
                    Bloc_nay_votes += 1
                else:
                    Bloc_Party_Size -= 1
            
            if Bloc_yea_votes >= Bloc_nay_votes:
                Bloc_Cohesion = round(Bloc_yea_votes / Bloc_Party_Size * 100, 2)
            else:
                Bloc_Cohesion = round(Bloc_nay_votes / Bloc_Party_Size * 100, 2)
        except ZeroDivisionError:
            Bloc_Cohesion = None
            
        # Green Cohesion
        try:
            Green_yea_votes = 0
            Green_nay_votes = 0
            for vote in party_votes[4]:
                if vote[1] == "Yea":
                    Green_yea_votes += 1
                elif vote[1] == "Nay":
                    Green_nay_votes += 1
                else:
                    Green_Party_Size -= 1
            
            if Green_yea_votes >= Green_nay_votes:
                Green_Cohesion = round(Green_yea_votes / Green_Party_Size * 100, 2)
            else:
                Green_Cohesion = round(Green_nay_votes / Green_Party_Size * 100, 2)
        except ZeroDivisionError:
            Green_Cohesion = None

        # Independent Cohesion
        try:
            Independent_yea_votes = 0
            Independent_nay_votes = 0
            for vote in party_votes[5]:
                if vote[1] == "Yea":
                    Independent_yea_votes += 1
                elif vote[1] == "Nay":
                    Independent_nay_votes += 1
                else:
                    Independent_Party_Size -= 1

            if Independent_yea_votes >= Independent_nay_votes:
                Independent_Cohesion = round(Independent_yea_votes / Independent_Party_Size * 100, 2)
            else:
                Independent_Cohesion = round(Independent_nay_votes / Independent_Party_Size * 100, 2)
        except ZeroDivisionError:
            Independent_Cohesion = None

        print()
        print(f"Conservative Cohesion: {Conservative_Cohesion}% (Party Size: {Conservative_Party_Size}, Yea Votes: {Conservative_yea_votes}, Nay Votes: {Conservative_nay_votes})")
        print(f"Liberal Cohesion: {Liberal_Cohesion}% (Party Size: {Liberal_Party_Size}, Yea Votes: {Liberal_yea_votes}, Nay Votes: {Liberal_nay_votes})")
        print(f"NDP Cohesion: {NDP_Cohesion}% (Party Size: {NDP_Party_Size}, Yea Votes: {NDP_yea_votes}, Nay Votes: {NDP_nay_votes})")
        print(f"Bloc Cohesion: {Bloc_Cohesion}% (Party Size: {Bloc_Party_Size}, Yea Votes: {Bloc_yea_votes}, Nay Votes: {Bloc_nay_votes})")
        print(f"Green Cohesion: {Green_Cohesion}% (Party Size: {Green_Party_Size}, Yea Votes: {Green_yea_votes}, Nay Votes: {Bloc_nay_votes})")
        print(f"Independent Cohesion: {Independent_Cohesion}% (Party Size: {Independent_Party_Size}, Yea Votes: {Independent_yea_votes}, Nay Votes: {Independent_nay_votes})")
    
        Party_Cohesion = [Conservative_Cohesion, Liberal_Cohesion, NDP_Cohesion, Bloc_Cohesion, Green_Cohesion, Independent_Cohesion]
        return Party_Cohesion

def plot_cohesion_by_party(party_cohesion):
    parties = ["Conservative", "Liberal", "NDP", "Bloc", "Green", "Independent"]

    # Convert non-numeric values to 0 or handle them appropriately
    numeric_cohesion = []
    for cohesion in party_cohesion:
        try:
            numeric_cohesion.append(float(cohesion))
        except ValueError:
            numeric_cohesion.append(0)  # or handle it as needed

    plt.figure(figsize=(10, 6))
    plt.bar(parties, numeric_cohesion, color=['blue', 'red', 'orange', 'lightblue', 'green', 'grey'])

    plt.xlabel('Parties')
    plt.ylabel('Cohesion (%)')
    plt.title('Party Cohesion')
    plt.ylim(0, 100)

    for i, cohesion in enumerate(numeric_cohesion):
        plt.text(i, cohesion + 1, f'{cohesion}%', ha='center')

    plt.show()

# Get a random parliament session and bill
def test_random_parliament_and_bill():
    directories = [d for d in os.listdir("./") if os.path.isdir(os.path.join("./", d))]
    directory = os.path.join("./", random.choice(directories))
    bill = random.choice(os.listdir(directory))
    party_votes = get_votes_by_party(directory, bill)
    Party_Cohesion = display_cohesion_by_party(party_votes)
    plot_cohesion_by_party(Party_Cohesion)

# Test a specific parliament session and bill
def test_parliament_and_bill():
    directory = "./Parliament_38-1"
    bill = "file_23.csv"
    party_votes = get_votes_by_party(directory, bill)
    Party_Cohesion = display_cohesion_by_party(party_votes)
    plot_cohesion_by_party(Party_Cohesion)

# Test a specific parliament session and all its bills
def test_parliament():
    directory = "./Parliament_44-1"
    party_votes = get_votes_by_party(directory)
    Party_Cohesion = display_cohesion_by_party(party_votes)
    plot_cohesion_by_party(Party_Cohesion)

# Plot the cohesion of each party over time for a random parliament session
def plot_rand_parliament_cohesion_over_time(excluded_parties=None, parliament=None):
    if excluded_parties is None:
        excluded_parties = []

    if parliament is None:
        directories = [d for d in os.listdir("./") if os.path.isdir(os.path.join("./", d))]
        directory = os.path.join("./", random.choice(directories))
    else:
        directory = parliament
    
    party_votes = get_votes_by_party(directory)

    cohesion_by_bill = []
    for vote in party_votes:
        Conservative_Party_Size = len(vote[0])
        Liberal_Party_Size = len(vote[1])
        NDP_Party_Size = len(vote[2])
        Bloc_Party_Size = len(vote[3])
        Green_Party_Size = len(vote[4])
        Independent_Party_Size = len(vote[5])

        bill = vote[6]

        # Conservative Cohesion
        try:
            Conservative_yea_votes = 0
            Conservative_nay_votes = 0
            for value in vote[0]:
                if value[1] == "Yea":
                    Conservative_yea_votes += 1
                elif value[1] == "Nay":
                    Conservative_nay_votes += 1
                else:
                    Conservative_Party_Size -= 1
            
            if Conservative_yea_votes >= Conservative_nay_votes:
                Conservative_Cohesion = round(Conservative_yea_votes / Conservative_Party_Size * 100, 2)
            else:
                Conservative_Cohesion = round(Conservative_nay_votes / Conservative_Party_Size * 100, 2)
        except ZeroDivisionError:
            Conservative_Cohesion = None
        
        # Liberal Cohesion
        try:
            Liberal_yea_votes = 0
            Liberal_nay_votes = 0
            for value in vote[1]:
                if value[1] == "Yea":
                    Liberal_yea_votes += 1
                elif value[1] == "Nay":
                    Liberal_nay_votes += 1
                else:
                    Liberal_Party_Size -= 1
            
            if Liberal_yea_votes >= Liberal_nay_votes:
                Liberal_Cohesion = round(Liberal_yea_votes / Liberal_Party_Size * 100, 2)
            else:
                Liberal_Cohesion = round(Liberal_nay_votes / Liberal_Party_Size * 100, 2)
        except ZeroDivisionError:
            Liberal_Cohesion = None
        
        # NDP Cohesion
        try:
            NDP_yea_votes = 0
            NDP_nay_votes = 0
            for value in vote[2]:
                if value[1] == "Yea":
                    NDP_yea_votes += 1
                elif value[1] == "Nay":
                    NDP_nay_votes += 1
                else:
                    NDP_Party_Size -= 1
            
            if NDP_yea_votes >= NDP_nay_votes:
                NDP_Cohesion = round(NDP_yea_votes / NDP_Party_Size * 100, 2)
            else:
                NDP_Cohesion = round(NDP_nay_votes / NDP_Party_Size * 100, 2)
        except ZeroDivisionError:
            NDP_Cohesion = None
        
        # Bloc Cohesion
        try:
            Bloc_yea_votes = 0
            Bloc_nay_votes = 0
            for value in vote[3]:
                if value[1] == "Yea":
                    Bloc_yea_votes += 1
                elif value[1] == "Nay":
                    Bloc_nay_votes += 1
                else:
                    Bloc_Party_Size -= 1
            
            if Bloc_yea_votes >= Bloc_nay_votes:
                Bloc_Cohesion = round(Bloc_yea_votes / Bloc_Party_Size * 100, 2)
            else:
                Bloc_Cohesion = round(Bloc_nay_votes / Bloc_Party_Size * 100, 2)
        except ZeroDivisionError:
            Bloc_Cohesion = None
        
        # Green Cohesion
        try:
            Green_yea_votes = 0
            Green_nay_votes = 0
            for value in vote[4]:
                if value[1] == "Yea":
                    Green_yea_votes += 1
                elif value[1] == "Nay":
                    Green_nay_votes += 1
                else:
                    Green_Party_Size -= 1
            
            if Green_yea_votes >= Green_nay_votes:
                Green_Cohesion = round(Green_yea_votes / Green_Party_Size * 100, 2)
            else:
                Green_Cohesion = round(Green_nay_votes / Green_Party_Size * 100, 2)
        except ZeroDivisionError:
            Green_Cohesion = None
        
        # Independent Cohesion
        try:
            Independent_yea_votes = 0
            Independent_nay_votes = 0
            for value in vote[5]:
                if value[1] == "Yea":
                    Independent_yea_votes += 1
                elif value[1] == "Nay":
                    Independent_nay_votes += 1
                else:
                    Independent_Party_Size -= 1

            if Independent_yea_votes >= Independent_nay_votes:
                Independent_Cohesion = round(Independent_yea_votes / Independent_Party_Size * 100, 2)
            else:
                Independent_Cohesion = round(Independent_nay_votes / Independent_Party_Size * 100, 2)
        except ZeroDivisionError:
            Independent_Cohesion = None

        cohesion_by_bill.append([[Conservative_Cohesion, Liberal_Cohesion, NDP_Cohesion, Bloc_Cohesion, Green_Cohesion, Independent_Cohesion], bill])

    cohesion_by_bill_sorted = sorted(cohesion_by_bill, key=lambda x: int(x[1].split('_')[1]))

    # Plotting cohesion_by_bill_sorted
    plt.figure(figsize=(20, 10))
    parties = ["Conservative", "Liberal", "NDP", "Bloc Quebecois", "Green", "Independent"]
    party_colors = {
        "Conservative": "#1C4587",  # Blue
        "Liberal": "#D71920",       # Red
        "NDP": "#F58220",          # Orange
        "Bloc Quebecois": "#33B2CC", # Light Blue
        "Green": "#3D9B35",        # Green
        "Independent": "#777777"    # Grey
    }
    # Filter out excluded parties
    included_indices = [i for i, party in enumerate(parties) if party not in excluded_parties]
    included_parties = [parties[i] for i in included_indices]
    
    for i, party in zip(included_indices, included_parties):
        cohesion_values = [cohesion[0][i] for cohesion in cohesion_by_bill_sorted]
        bills = [cohesion[1].split('_')[1] for cohesion in cohesion_by_bill_sorted]
        plt.plot(bills, cohesion_values, 
                 label=party,
                 color=party_colors[party], 
                 marker='o', 
                 linestyle='-', 
                 markersize=6, 
                 alpha=0.5)

    plt.xlabel('Bills')
    plt.ylabel('Cohesion')
    plt.title(f'Party Cohesion: {directory}')
    plt.xticks(rotation=45, ha='right', fontsize=2)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout(pad=3, w_pad=5)
    plt.savefig('cohesion_by_bill_sorted.png')


if __name__ == "__main__":
    # test_parliament()
    plot_rand_parliament_cohesion_over_time(['Independent'])
