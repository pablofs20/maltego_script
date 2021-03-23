import sys
import bs4
import re
import requests
import base64
import numpy as np
from selenium import webdriver
from maltego_trx.transform import MaltegoTransform

def initialize_selenium():
	# Start firefox driver in headless mode (doesn't pop up)
	options = webdriver.FirefoxOptions()
	options.add_argument("--headless")
	driver = webdriver.Firefox(options = options)

	return driver

def search_user(driver, email):
	# Navigate to Directorio UM URL
	driver.get("https://www.um.es/atica/directorio/")

	# Complete and send search form (navigates to user specific page)
	username_input = "//*[@id=\"texto\"]"
	search_button = "/html/body/div/div/div/table/tbody/tr/td[2]/center/div/table[1]/tbody/tr[1]/td/input[2]"
	driver.find_element_by_xpath(username_input).send_keys(email)
	driver.find_element_by_xpath(search_button).click()

	# Get user's page URL and content
	user_url = driver.current_url
	user_html = requests.get(user_url).text

	return user_html

def get_user_data(user_html, m):
	user_data = {}

	soup = bs4.BeautifulSoup(user_html, "html.parser")

	prop_name = soup.find_all("span", itemprop = "name")
	
	person_name = prop_name[2]
	if person_name is not None:
		person_name = person_name.text.strip()
		m.addEntity("maltego.Person", person_name)

	org_unit = prop_name[3]
	if org_unit is not None:
		org_unit = org_unit.text.strip()
		#m.addEntity("um.OrganizationalUnit", org_unit)

	faculty = soup.find("span", itemprop = "streetAddress")
	if faculty is not None:
		faculty = faculty.contents[0]
		#m.addEntity("um.Faculty", faculty)

	position = soup.find("span", itemprop = "jobTitle")
	if position is not None:
		position = position.text.strip()
		#m.addEntity("um.Position", position)

	affiliation = soup.find("td", width = "60%")
	if affiliation is not None:
		affiliation = affiliation.text.strip()
		#m.addEntity("um.Affiliation", affiliation)

	area = soup.find('td', text = re.compile('Area de Conocimiento:'), attrs = {'class' : 'derecha'})
	if area is not None:
		area = area.find_next_sibling('td', {'nowrap' : ''}).text.strip()
		#m.addEntity("um.Area", area)

	phone = soup.find("span", itemprop = "telephone")
	if phone is not None:
		phone = phone.text.strip()
		#m.addEntity("um.PhoneNumber", phone)

	office = soup.find("a", itemprop = "workLocation")
	if office is not None:
		office = office.text.strip()
		#m.addEntity("um.Office", office)

	personal_um_page = soup.find("a", itemprop = "url", title = "Ver la web personal institucional")
	if personal_um_page is not None:
		personal_um_page = personal_um_page.text.strip()
		#m.addEntity("um.PersonalUMPage", personal_um_page)

	academic_cv = soup.find('td', text = re.compile('Currículum académico:'), attrs = {'class' : 'derecha'})
	if academic_cv is not None:
		academic_cv = academic_cv.find_next_sibling('td', {'nowrap' : ''}).text.strip()
		#m.addEntity("um.AcademicCV", academic_cv)

def add_cargo(driver, email, m):
	search_user(driver, email)
	cargo_link = "/html/body/div/div/div/table/tbody/tr/td[2]/center/div/table[4]/tbody/tr/td/table/tbody/tr/td[2]/table/tbody/tr[3]/td/a"
	driver.find_element_by_xpath(cargo_link).click()
	cargo_html = requests.get(driver.current_url).text

	soup = bs4.BeautifulSoup(cargo_html, "html.parser")
	cargo = soup.find('td', text = re.compile('Cargo:'), attrs = {'class' : 'derecha'}).find_next_sibling('td', {'nowrap' : ''}).text.strip()
	
	m.addEntity("um.SpecialPosition", cargo)

# If user has cargo (multiple entries), gets user page
def get_user_page(driver):
	user_page_link = "/html/body/div/div/div/table/tbody/tr/td[2]/center/div/table[4]/tbody/tr/td/table/tbody/tr/td[2]/table/tbody/tr[1]/td/a"
	driver.find_element_by_xpath(user_page_link).click()
	user_html = requests.get(driver.current_url).text

	return user_html

def check_cargo(user_html, driver):
	soup = bs4.BeautifulSoup(user_html, "html.parser")

	cargo = soup.find("img", title = "Cargo")

	if cargo is not None:
		return True
	else:
		return False

def check_multiple_results(user_html, email):
	soup = bs4.BeautifulSoup(user_html, "html.parser")
	results_table = soup.find_all("table", summary = "Directorio corporativo de la Universidad de Murcia.")[5]
	
	results = results_table.find_all("tr", recursive = False)

	if len(results) > 1:
		return [True, results]
	else:
		return [False, None]

def get_correct_user(results, email):
	for result in results:
		user_page_link = result.find('a').attrs['href']
		user_page_link = "https://www.um.es/atica/directorio/" + user_page_link
		user_html = requests.get(user_page_link).text
		soup = bs4.BeautifulSoup(user_html, "html.parser")
		email_script = str(soup.find('td', text = re.compile('Correo electrónico:'), attrs = {'class' : 'derecha'}).find_next_sibling('td', {'nowrap' : ''}).find('script'))
		search_result = re.search('correo\(\'(.*)\'\,\'(.*)\,', email_script)
		email_parts_encoded = search_result.group(1).replace('\'', '').split(',')
		email_parts_decoded = []
		for email_part in email_parts_encoded:
			email_part_decoded = base64.b64decode(email_part).decode('ascii')
			email_parts_decoded.append(email_part_decoded)
		
		email_obtained = email_parts_decoded[1] + "@" + email_parts_decoded[0]

		if email_obtained == email:
			return user_html
	
def check_correct_email(user_page_link, email):
	user_html = requests.get(user_page_link).text
	soup = bs4.BeautifulSoup(user_html, "html.parser")
	email_script = str(soup.find('td', text = re.compile('Correo electrónico:'), attrs = {'class' : 'derecha'}).find_next_sibling('td', {'nowrap' : ''}).find('script'))
	search_result = re.search('correo\(\'(.*)\'\,\'(.*)\,', email_script)
	email_parts_encoded = search_result.group(1).replace('\'', '').split(',')
	email_parts_decoded = []
	for email_part in email_parts_encoded:
		email_part_decoded = base64.b64decode(email_part).decode('ascii')
		email_parts_decoded.append(email_part_decoded)
	
	email_obtained = email_parts_decoded[1] + "@" + email_parts_decoded[0]
	
	if email_obtained == email:
		return user_html


if __name__ == "__main__":
	# Gets email from command line parameters
	email = sys.argv[2]

	m = MaltegoTransform()

	driver = initialize_selenium()

	user_html = search_user(driver, email)

	[multiple_results, results] = check_multiple_results(user_html, email)

	has_cargo = check_cargo(user_html, driver)

	if multiple_results and not has_cargo:
		user_html = get_correct_user(results, email)
		get_user_data(user_html, m)

	elif multiple_results and has_cargo:
		user_html = get_correct_user(results, email)
		get_user_data(user_html, m)
		#add_cargo(driver, email, m)

	elif has_cargo and not multiple_results:
		user_html = get_user_page(driver)
		get_user_data(user_html, m)
		#add_cargo(driver, email. m)

	else:
		get_user_data(user_html, m)

	print(m.returnOutput())
