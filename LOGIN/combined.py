import os
from groq import Groq
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import re
import fitz  # For reading PDFs
import spacy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import csv
import json

# Initialize Groq client
client = Groq(api_key="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")

# Load the spaCy NLP model for experience extraction
nlp = spacy.load("en_core_web_sm")

# Predefined skill keywords
skill_keywords_set = {
    "python", "java", "c++", "c", "javascript", "html", "css", "sql",
    "statistical analysis", "report generation", "spreadsheet analysis", "mail distribution",
    "data structures", "data analysis", "machine learning", "deep learning", "nlp", "computer vision",
    "excel", "tableau", "data visualization", "data engineering", "team collaboration", "project management",
    "problem solving", "communication", "leadership", "agile", "python programming", "software development"
}

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as pdf:
        text = ""
        for page in pdf:
            text += page.get_text()
    return text

# Function to extract skills from text
def extract_skills_from_section(text):
    skill_section_keywords = ["skills", "technical skills", "key skills", "core skills"]
    skill_section_pattern = re.compile(r"(?i)(skills|technical skills|key skills|core skills)[^\n]*\n([\s\S]*?)(?=\n[A-Za-z ]+|$)")
    match = skill_section_pattern.search(text)
    
    skills = []
    if match:
        skill_section_text = match.group(2).strip()
        skill_lines = skill_section_text.split("\n")
        
        for line in skill_lines:
            skills_in_line = [word.strip() for word in line.split(",") if word.strip().lower() in skill_keywords_set]
            skills.extend(skills_in_line)
    return list(set(skills))

# Function to extract experience and keywords using NLP
def extract_keywords_nlp(text):
    doc = nlp(text)
    keywords = {
        "skills": [],
        "experience": [],
        "projects": []
    }

    # Define section trigger keywords for experience
    experience_keywords = {"experience", "employment", "work"}

    # Iterate through sentences to identify sections
    for sent in doc.sents:
        sent_text = sent.text.strip().lower()

        # Detect experience
        if any(word in sent_text for word in experience_keywords):
            keywords["experience"].append(sent.text)

    # Deduplicate experience
    keywords["experience"] = list(set(keywords["experience"]))  # Deduplicate experience

    return keywords

# Function to interact with Groq API
def generate_job_titles_groq(data):
    try:
        prompt = f"""
        Based on the following data, provide at most 5 job titles in a numbered list format. 
        Do not include any additional text or details. The list should only consist of job titles:
        
        {data}
        """
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192"
        )
        
        # Extract the generated content
        return response.choices[0].message.content
    except Exception as e:
        return f"Error occurred while interacting with Groq API: {e}"

# Function to extract job titles from Groq API response
def extract_job_titles(text):
    pattern = r"^\s*\d+\.\s*(.+)"
    matches = re.findall(pattern, text, re.MULTILINE)
    return [title.strip() for title in matches]

# Function to scrape job listings from Naukri.com based on job titles
# Function to scrape job listings from Naukri.com based on job titles
def extract_skills_groq(promt):
   
    # Call the function from groqsorting.py
    skills  = client.chat.completions.create(
            messages=[{"role": "user", "content": promt}],
            model="llama3-8b-8192"
        )
    return skills.choices[0].message.content
def sort_jobs_by_compatability(job_data):
    # Sort the jobs based on the 'Compatability' field in descending order
    sorted_jobs = sorted(job_data, key=lambda job: job['Compatability'], reverse=True)
    return sorted_jobs
def scrape_jobs_from_naukri(job_titles,user_skill):
    job_data = []  # Store job details in a list

    # Initialize WebDriver
    driver = webdriver.Chrome()

    try:
        # Open Naukri.com
        driver.get("https://www.naukri.com/")

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Enter skills / designations / companies']"))
        )

        for job_title in job_titles:
            print(f"\nSearching for '{job_title}'...")

            # Enter job title
            job_title_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Enter skills / designations / companies']")
            job_title_input.clear()
            job_title_input.send_keys(job_title)

            # Enter location
            location_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Enter location']")
            location_input.clear()
            location_input.send_keys("Bangalore")

            # Click the search button
            search_button = driver.find_element(By.CLASS_NAME, "qsbSubmit")
            search_button.click()

            # Wait for job listings to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.cust-job-tuple.layout-wrapper.lay-2.sjw__tuple"))
            )

            # Locate job listings container
            job_listings = driver.find_elements(By.CSS_SELECTOR, "div.cust-job-tuple.layout-wrapper.lay-2.sjw__tuple")

            if job_listings:
                for job in job_listings:

                    try:
                        # Extract details for each job
                        title = job.find_element(By.CSS_SELECTOR, "a.title").text
                        company = job.find_element(By.CSS_SELECTOR, "a.comp-name").text
                        location = job.find_element(By.CSS_SELECTOR, "span.locWdth").text
                        experience = job.find_element(By.CSS_SELECTOR, "span.expwdth").text
                        job_link = job.find_element(By.CSS_SELECTOR, "a.title").get_attribute("href")

                        # Extract skills (handle errors gracefully)
                        try:
                            skills = job.find_element(By.XPATH, "/html/body/div/div/main/div[1]/div[2]/div[2]/div/div[1]/div/div[5]/ul").text
                        except Exception:
                            skills = "Not specified"

                        # Print extracted skills
                        print(f"Skills: {skills}")
                        promt=f"Compare the user's skills and the job's required skills. Check all the skills mentioned and return a single compatibility score between 0 and 100, based on how many skills match. Provide only the number as the result, with no additional text or details.User Skills: {user_skill} ,Job Skills: {skills}"

                        current_comp = extract_skills_groq(promt)

                        # Store job details in job_data list (excluding skills)
                        job_data.append({
                            "title": title,
                            "company": company,
                            "location": location,
                            "experience": experience,
                            "job_link": job_link,
                            "Compatability":int(current_comp)
                        })

                        # Print details for debugging
                        print(f"Job Title: {title}")
                        print(f"Company: {company}")
                        print(f"Location: {location}")
                        print(f"Experience: {experience}")
                        print(f"Job Link: {job_link}")
                        print(f"SCORE:{current_comp}")
                    except Exception as job_error:
                        print(f"Error processing job: {job_error}")
                        skills = "Not specified"  # Set skills to "Not specified" if there's any error

            else:
                print(f"No job listings found for '{job_title}'.")

            # Go back to the homepage for the next search
            driver.get("https://www.naukri.com/")

            # Wait for the page to load again before searching for the next job
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Enter skills / designations / companies']"))
            )

            # Reset for the next search
            time.sleep(2)

    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the browser
        driver.quit()
    job_data =sort_jobs_by_compatability(job_data)
    # Save job data to a JSON file in the static folder
    with open("static/job_data.json", "w") as json_file:
        json.dump(job_data, json_file, indent=4)

    return job_data  # Return job data to display in cards
def scrape_job_data(job_titles, user_skill,browser="chrome"):
    # Set up WebDriver
    print("Initializing WebDriver...")
    driver = webdriver.Chrome()

    # List to hold the job data
    job_data = []

    try:
        # Open CareerJet website
        print("Navigating to CareerJet website...")
        driver.get("https://www.careerjet.co.in")

        # Start job search (before login)
        print("Starting job search before login...")
        try:
            job_title_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "s"))
            )
            print("Job title field located.")
            job_title_field.clear()
            job_title_field.send_keys("Software Engineer")

            location_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "l"))
            )
            print("Location field located.")
            location_field.clear()
            location_field.send_keys("Bangalore")

            submit_button = driver.find_element(By.CLASS_NAME, "btn-primary")
            print("Search button located. Submitting search...")
            submit_button.click()

            # Wait for search results to load
            print("Waiting for search results...")
            time.sleep(3)
        except Exception as e:
            print(f"Error during initial search: {e}")

        # Proceed to login
        print("Logging in with provided credentials...")
        try:
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/main/div/form/div/p[1]/input"))
            )
            print("Email field found. Entering email...")
            email_field.clear()
            email_field.send_keys("skandazoro@gmail.com")

            password_field = driver.find_element(By.XPATH, "/html/body/main/div/form/div/p[2]/span/input")
            print("Password field found. Entering password...")
            password_field.clear()
            password_field.send_keys("skanda888")

            submit_button = driver.find_element(By.XPATH, "/html/body/main/div/form/div/p[3]/button")
            print("Login button found. Logging in...")
            submit_button.click()

            print("Waiting for login process to complete...")
            time.sleep(5)

            print("Navigating back to homepage after login...")
            driver.get("https://www.careerjet.co.in")
        except Exception as e:
            print(f"Error during login: {e}")

        # Loop through job titles and perform search and extraction for each title
        for job_title in job_titles:
            print(f"\nStarting job search for: {job_title}")

            try:
                job_title_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "s"))
                )
                print(f"Job title field located for {job_title}.")
                job_title_field.clear()
                job_title_field.send_keys(job_title)

                location_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "l"))
                )
                print("Location field located.")
                location_field.clear()
                location_field.send_keys("Bangalore")

                submit_button = driver.find_element(By.CLASS_NAME, "btn-primary")
                print(f"Search button located for {job_title}. Submitting search...")
                submit_button.click()

                # Wait for search results to load
                time.sleep(3)
            except Exception as e:
                print(f"Error during search for {job_title}: {e}")

            # Locate and handle job listings
            try:
                jobs_list = driver.find_elements(By.XPATH, "/html/body/main/div/div/div/ul/li")
                if not jobs_list:
                    print("No job listings found!")
                    continue  # Skip to the next job title

                # Limit to first 5 job listings
                for i in range(min(5, len(jobs_list))):
                    print(f"\nScraping job listing {i + 1} for {job_title}...")

                    job = jobs_list[i]
                    job_link = job.find_element(By.XPATH, "/html/body/main/div/div/div/ul/li[2]/article/header")
                    job_link.click()

                    # Wait for job details page to load
                    time.sleep(3)

                    job_details_container = driver.find_element(By.XPATH, "/html/body/main/article/div")

                    title = job_details_container.find_element(By.XPATH, "header/h1").text

                    location = job_details_container.find_element(By.XPATH, "header/ul[1]/li[1]").text

                    qualifications = job_details_container.find_element(By.XPATH, "section[1]/ul[2]").text

                    # Extract skills
                    try:
                        # Locate the container or section that might contain skills
                        skills_section = job_details_container.find_element(By.XPATH, "section[1]")  # Adjust the XPath if needed
                        print("Skills section found. Extracting content...")

                        # Extract all text from the section
                        skills_text = skills_section.text
                        print(f"Skills or related content extracted:\n{skills_text}")
                    except Exception as e:
                        print("Skills section not found or an error occurred.")
                        skills_text = "Not listed"

                    # Extract job link from the provided XPath
                    try:
                        job_link_element = driver.find_element(By.XPATH, "/html/body/main/article/div/section[2]/ul/li[2]/a")
                        job_url = job_link_element.get_attribute("href")
                        print(f"Job Link from second section: {job_url}")
                    except Exception as e:
                        print("Error extracting job link from second section.")
                        job_url = "Not listed"

                    # Extract company name from the provided XPath
                    try:
                        company_name_element = driver.find_element(By.XPATH, "/html/body/main/article/div/header/p/a")
                        company_name = company_name_element.text
                        print(f"Company Name: {company_name}")
                    except Exception as e:
                        company_name = "Not listed"
                    prompt = "here take the data and give me the experince required for this job and only give me the experince no other details"+qualifications
                    experince =extract_skills_groq(prompt)
                    prompt = f"""compare the user's skills and the job's required skills. Check all the skills mentioned and return a single compatibility score between 0 and 100, based on how many skills match. Provide only the number as the result, with no additional text or details.userskills:{user_skill}, jobskills:{skills_text}"""
                    current_comp =extract_skills_groq(prompt)

                    # Store job details in the job_data list
                    job_data.append({
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "qualifications": experince,
                        "job_link": job_url,
                        'Compatability':int(current_comp)
                         # Added company name
                    })
                    print(job_data,'here is job data')
                    

                    

                    # Go back to the search results page
                    print("Navigating back to search results page...")
                    driver.back()
                    time.sleep(3)  # Wait for the page to load again

                    # Re-fetch the job listings
                    jobs_list = driver.find_elements(By.XPATH, "/html/body/main/div/div/div/ul/li")
                    if i == len(jobs_list) - 1:
                        break  # If it's the last job, exit the loop

            except Exception as e:
                print(f"Error while handling job listings for {job_title}: {e}")

            # After scraping 5 jobs for the current job title, go back to the homepage and move to the next title
            print("Navigating back to homepage after completing this job title...")
            driver.get("https://www.careerjet.co.in")
            time.sleep(3)  # Wait for the page to load
        

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()
        
        job_data =sort_jobs_by_compatability(job_data)
    # Save job data to a JSON file in the static folder
        with open("static/job_data.json", "w") as json_file:
            json.dump(job_data, json_file, indent=4)

        return job_data  # Return job data to display in cards 
# Main function
def main():
    if len(sys.argv) < 3:
        print("Usage: python combined.py <pdf_path> <job_board>")
        return
    
    pdf_path = sys.argv[1]  # First argument is the PDF file path
    job_board = sys.argv[2]  
    try:
        # Extract text from the resume
        text = extract_text_from_pdf(pdf_path)
        
        # Extract skills
        skills = extract_skills_from_section(text)
        
        # Extract keywords like experience using NLP
        keywords = extract_keywords_nlp(text)
        
        # Prepare the data for Groq API (Skills and Experience)
        input_data = f"Skills: {', '.join(skills)}\nExperience: {', '.join(keywords['experience'])}"
        
        # Generate job titles using Groq API
        job_titles_text = generate_job_titles_groq(input_data)
        skill_promt ="""
    Based on the following data, extract all skills mentioned in the text.  
Return the skills as a numbered list format without limiting the number of items.  
Do not include any additional text or details. The list should only consist of skills:
    """+input_data

        user_skills =extract_skills_groq(skill_promt)
        user_skills=extract_job_titles(user_skills)
        # Extract job titles from the response
        job_titles = extract_job_titles(job_titles_text)
        
        # Print the extracted job titles
        print("\nExtracted Job Titles:")
        for title in job_titles:
            print(title)

        # Scrape job listings from Naukri based on extracted job titles
        if job_board == "naukri":
            jobs_data = scrape_jobs_from_naukri(job_titles, str(user_skills))
        elif job_board == "careerjet":
            jobs_data = scrape_job_data(job_titles, str(user_skills))
        else:
            print("Unsupported job board")

       
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()