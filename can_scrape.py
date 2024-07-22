import requests
from bs4 import BeautifulSoup
import csv
import os


def get_vote_pages(session):
    vote_url = "https://www.ourcommons.ca/members/en/votes?parlSession="
    house_of_commons = vote_url + session
    response = requests.get(house_of_commons)
    
    if response.status_code == 500:
        return response.status_code

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
    
    return 0
    
def get_vote_by_party(vote_pages, output_name):
    with open(vote_pages, mode='r') as file:
        csv_reader = csv.reader(file)

        if not os.path.exists(output_name):
            os.makedirs(output_name)

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
                        vote_url = vote_url[-4:]
                        while "/" in vote_url:
                            vote_url = vote_url[1:]
                        file_name = f"file_{vote_url}.csv"
                        file_path = os.path.join(output_name, file_name)
                        with open(file_path, 'wb') as file:
                            file.write(file_response.content)


if __name__ == "__main__":
        for i in range(38, 42):
            for j in range(1, 4):
                session = str(i) + "-" + str(j)
                response = get_vote_pages(session)
                if response == 0:
                    output_name = "./Parliament_" + session + "/"
                    get_vote_by_party('./output.csv', output_name)


