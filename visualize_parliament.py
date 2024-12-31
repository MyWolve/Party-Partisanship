import os
import csv


def get_votes_by_party(directory, bill):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        if os.path.isfile(file_path) and bill in file_path:
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                # Skip the header row
                header = next(reader)

                voters = list(reader)
                print(f"Number of voters: {len(voters)}")
                # Prints name of file
                print(f"Bill: {filename}")

                # Count the number of votes by party and return them as lists
                Conservative_Votes = []
                Liberal_Votes = []
                NDP_Votes = []
                Bloc_Votes = []
                Green_Votes = []
                Independent_Votes = []

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


                Party_Votes = [Conservative_Votes, Liberal_Votes, NDP_Votes, Bloc_Votes, Green_Votes, Independent_Votes]

    return Party_Votes

def display_cohesion_by_party(party_votes):
    # Party cohesion is defined as the percentage of votes that are the same as the party leader's vote
    Conservative_Party_Size = len(party_votes[0])
    Liberal_Party_Size = len(party_votes[1])
    NDP_Party_Size = len(party_votes[2])
    Bloc_Party_Size = len(party_votes[3])
    Green_Party_Size = len(party_votes[4])
    Independent_Party_Size = len(party_votes[5])

    # Conservative Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[0]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1
        
        if yea_votes >= nay_votes:
            Conservative_Cohesion = yea_votes / Conservative_Party_Size * 100
        else:
            Conservative_Cohesion = nay_votes / Conservative_Party_Size * 100
    except ZeroDivisionError:
        Conservative_Cohesion = "N/A"

    # Liberal Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[1]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1
        
        if yea_votes >= nay_votes:
            Liberal_Cohesion = yea_votes / Liberal_Party_Size * 100
        else:
            Liberal_Cohesion = nay_votes / Liberal_Party_Size * 100
    except ZeroDivisionError:
        Liberal_Cohesion = "N/A"
    
    # NDP Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[2]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1
        
        if yea_votes >= nay_votes:
            NDP_Cohesion = yea_votes / NDP_Party_Size * 100
        else:
            NDP_Cohesion = nay_votes / NDP_Party_Size * 100
    except ZeroDivisionError:
        NDP_Cohesion = "N/A"
    
    # Bloc Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[3]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1
        
        if yea_votes >= nay_votes:
            Bloc_Cohesion = yea_votes / Bloc_Party_Size * 100
        else:
            Bloc_Cohesion = nay_votes / Bloc_Party_Size * 100
    except ZeroDivisionError:
        Bloc_Cohesion = "N/A"
        
    # Green Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[4]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1
        
        if yea_votes >= nay_votes:
            Green_Cohesion = yea_votes / Green_Party_Size * 100
        else:
            Green_Cohesion = nay_votes / Green_Party_Size * 100
    except ZeroDivisionError:
        Green_Cohesion = "N/A"

    # Independent Cohesion
    try:
        yea_votes = 0
        nay_votes = 0
        for vote in party_votes[5]:
            if vote[1] == "Yea":
                yea_votes += 1
            else:
                nay_votes += 1

        if yea_votes >= nay_votes:
            Independent_Cohesion = yea_votes / Independent_Party_Size * 100
        else:
            Independent_Cohesion = nay_votes / Independent_Party_Size * 100
    except ZeroDivisionError:
        Independent_Cohesion = "N/A"

    print()
    print(f"Conservative Cohesion: {Conservative_Cohesion}%")
    print(f"Liberal Cohesion: {Liberal_Cohesion}%")
    print(f"NDP Cohesion: {NDP_Cohesion}%")
    print(f"Bloc Cohesion: {Bloc_Cohesion}%")
    print(f"Green Cohesion: {Green_Cohesion}%")
    print(f"Independent Cohesion: {Independent_Cohesion}%")


directory = "./Parliament_38-1"
bill = "file_1.csv"
party_votes = get_votes_by_party(directory, bill)
display_cohesion_by_party(party_votes)