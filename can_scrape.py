import requests
from bs4 import BeautifulSoup
import csv
import os


def get_vote_pages():
    house_of_commons = "https://www.ourcommons.ca/members/en/votes" 
    response = requests.get(house_of_commons)
    html_content = response.text

    soup = BeautifulSoup(html_content, "html.parser")

    tbody = soup.find("tbody")

    with open('/home/mgday/repos/Party-Partisanship/output.csv', mode='w', newline='', encoding='utf-8') as f:    
        writer = csv.writer(f)
        for tr in tbody.find_all('tr'):
            td = tr.find('td')
            if td:
                a_tag = td.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    data_row = ["https://www.ourcommons.ca" + a_tag['href']]
                    writer.writerow(data_row)
    
def get_vote_by_party(vote_pages):
    with open(vote_pages, mode='r') as file:
        csv_reader = csv.reader(file)

        if not os.path.exists("votes_by_party"):
            os.makedirs("votes_by_party")

        for row in csv_reader:
            vote_url = row[0]
            
            response = requests.get(vote_url)
            html_content = response.text

            soup = BeautifulSoup(html_content, "html.parser")

            div = soup.find('div', class_='pt-2')

            if div:
                a_tags = div.find_all('a')

                if len(a_tags) >= 2:
                    csv_tag = a_tags[1]
                    href = csv_tag.get('href')

                    file_response = requests.get("https://www.ourcommons.ca" + href)
                    if file_response.status_code == 200:
                        vote_url = vote_url[-3:]
                        while "/" in vote_url:
                            vote_url = vote_url[1:]
                        file_name = f"file_{vote_url}.csv"
                        file_path = os.path.join('./votes_by_party/', file_name)
                        with open(file_path, 'wb') as file:
                            file.write(file_response.content)


if __name__ == "__main__":
    get_vote_by_party('./output.csv')

