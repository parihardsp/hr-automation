import streamlit as st
import requests


# Function to fetch top resumes based on job_id
def fetch_top_resumes(job_id):
    url = f"http://127.0.0.1:8000/api/fetch-top-resumes/{job_id}"  # Local API endpoint
    response = requests.get(url)
    st.write(f"API URL: {url}")  # Print the API URL
    st.write(f"Response Status Code: {response.status_code}")  # Print the response status code
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data from the server: {response.text}")  # Display error message
        return []


# Streamlit UI
st.title("Top Candidates for Job ID")

# Input for Job ID
job_id_input = st.text_input("Enter Job ID", placeholder="Enter a number")

if st.button("Fetch Candidates"):
    if job_id_input.isdigit():  # Check if the input is numeric
        job_id = int(job_id_input)  # Convert input to integer
        # Fetch resumes
        candidates = fetch_top_resumes(job_id)

        if candidates:
            for index, candidate in enumerate(candidates):
                # Candidate details
                candidate_id = candidate['candidate_id']
                first_name = candidate['first_name']
                last_name = candidate['last_name']
                overall_score = candidate['overall_score']

                # Calculate matching percentages
                match_details = candidate['match_details']
                skill_match = next((md for md in match_details if md['name'] == "Skills Match"), None)
                experience_match = next((md for md in match_details if md['name'] == "Experience Match"), None)
                education_match = next((md for md in match_details if md['name'] == "Education Match"), None)

                skill_percentage = (skill_match['score'] / skill_match['max_score']) * 100 if skill_match else 0
                experience_percentage = (experience_match['score'] / experience_match[
                    'max_score']) * 100 if experience_match else 0
                education_percentage = (education_match['score'] / education_match[
                    'max_score']) * 100 if education_match else 0

                # Company Background details
                company_bg_details = candidate.get('company_bg_details')

                # Display candidate information
                st.markdown(f"### Candidate {index + 1}: {first_name} {last_name} (Overall Score: {overall_score})")
                st.markdown(f"**Candidate ID:** {candidate_id}")
                st.markdown("### Match Percentages:")
                st.markdown(f"**Skills Match:** {skill_percentage:.2f}%")
                st.markdown(f"**Experience Match:** {experience_percentage:.2f}%")
                st.markdown(f"**Education Match:** {education_percentage:.2f}%")
                st.markdown("### Candidate Company Background Details:")

                if company_bg_details:
                    # Company details
                    for company in company_bg_details:
                        st.markdown(f"**Company:** {company['company']}")
                        st.markdown(f"**Industry:** {company['Industry']}")
                        st.markdown(f"**No of Employees:** {company['noEmployees']}")
                        st.markdown(f"**Foundation Year:** {company['formationYear']}")
                        st.markdown(f"**Type:** {company['type']}")
                        st.markdown("")  # For spacing between company details
                else:
                    st.markdown("No company background details available.")

                # Candidate URL
                st.markdown(f"**Link:** [View Candidate Profile]({candidate['url']})")

                # Separator line between candidates
                st.markdown("---")  # Horizontal line to separate candidates

        else:
            st.write("No candidates found for the given Job ID.")
    else:
        st.error("Please enter a valid numeric Job ID.")  # Error message for invalid input
