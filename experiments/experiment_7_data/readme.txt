#Last update: March 15, 2018

How to cite: 

Godbout, Jean-François and Bjørn Høyland. 2017. Canadian Parliament Voting Data, 1867-2015. Compiled by Jean-François Godbout, University of Montreal. Political Science Department. 

Scope of study:

Each file contains the results of all of the votes (divisions) recorded by the Hansards Journals in each parliament since Confederation. The files are organized by parliament (1st to 40th). The votes are organized by dates, and by the voting records of members. I also have the 41st and 42nd (1 session) data if you need it (but with MP names, riding, and party only). However, it’s in a different format (you can download directly the votes from the Parliamentary website).

To get the election results, use the Election Canada data file and match on election year (date) and riding code with the file : Elections-1867-2015.csv 
*Warning* matching the voting data with the election data by riding name, last-name, first-name, date of election, is the best way to go. But you will get some errors, as some MPs and candidates have the same name in the same election/riding, and by-elections can sometimes pause a problem.  

Finally, I have another data-file (not in the folder) with the description of each recorded division (sponsor, type of bill, motion, origin government-private member, topic, etc.). I’m happy to share this as well, but we should talk about collaborating if you want to use this data. 

########################
#Description of the variables#
########################

Coding of the votes: yes=1;no=2;paired=3;yes+no=4;yes+paired=5;no+paired=6;yes+no+paired=7;abstain (Senate only)=8,not-vote=9;no-sitting=99 (member is not sitting in the House);error=9999

Riding.code: From the History of Federal Ridings Parliament data-file

Riding: From the History of Federal Ridings Parliament data-file

Province: From the History of Federal Ridings Parliament data-file	

Riding.history: From the History of Federal Ridings Parliament data-file	

Parliament.no: 1-40	

Term: Dates in which the member was elected to the House in the current parliament, or affiliated with a specific political party. Thus, members who switch parties, or who are expelled have different term length. 

Id.2: A code to identify each specific member of the House of Commons. Members who switch party, or become independent, take a new value each time their status changes in the House, e.g. A member who left the Liberal Party in a parliament, first to sit as an independent, and than later to join the Conservative Party would be coded as follow: 1010 (Liberal), 1010.1 (independent), 1010.2 (joined the Conservatives).

Id: This is the html item tag from the Canadian Parliament Parliamentarian file for each member elected to the House found in the PARLINFO website. This code is no longer used by the PARLINFO. Chris Cochrane at UofT has a matching file (old and new codes).

Name: Name of the MP, from the History of Federal Ridings Parliament data-file

Party.Name: Party name from the PARLINFO website	

Occupation: Occupation from the PARLINFO website	

Religion: Coded by Godbout and Høyland, mostly from the Canadian Parliamentary Guides. 

French: Coded by Godbout and Høyland	

Length: Coded by Godbout and Høyland, number of terms served. 

switch.check: Coded by Godbout and Høyland, members who left a party during a parliament.

Ministry: Coded by Godbout and Høyland, members who were in the Cabinet during a parliament.

Secretary:  Coded by Godbout and Høyland, members who were in a parliament secretary during a parliament.

Change.party: Coded by Godbout and Høyland, members who left a party during a parliament (same as switch.check)

Temporary.suspended.caucus: Coded by Godbout and Høyland, members who were temporary suspended from the caucus (NOT USED)

Excluded.caucus: Coded by Godbout and Høyland, members who were excluded from the caucus (NOT USED)	

Quit.caucus: Coded by Godbout and Høyland, members who left their caucus (NOT USED)	

First.Nations: Members who are First Nation people, from the PARLINFO website.

Country.of.Birth: Country in which a member was born, from the PARLINFO website.

Note1: Notes about the MP

Note2: Notes about the MP	

vote.id: The ID of the recorded division in Parliament. For example, H01S1V001 stands for H(House)01(Session number)V001(vote number).

Date: Date of the recorded division. Two formats, need to clean this. day.month.year or year.month.day. Le me know if you are willing to change this for me!

