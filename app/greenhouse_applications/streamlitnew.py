import streamlit as st

# Dummy data for candidates
dummy_candidates = [
    {
        "candidate_id": "C001",
        "first_name": "John",
        "last_name": "Smith",
        "overall_score": "85.5",
        "match_details": [
            {
                "name": "Skills Match",
                "score": 25,
                "max_score": 30,
                "overview": "Strong technical skills matching job requirements"
            },
            {
                "name": "Experience Match",
                "score": 28,
                "max_score": 30,
                "overview": "Relevant experience in similar roles"
            },
            {
                "name": "Education Match",
                "score": 18,
                "max_score": 20,
                "overview": "Educational background aligns well with position"
            }
        ],
        "company_bg_details": [
            {
                "company": "Tech Solutions Inc.",
                "Industry": "Information Technology",
                "noEmployees": "1000-5000",
                "formationYear": "1995",
                "type": "Public Corporation"
            },
            {
                "company": "Digital Innovations Ltd",
                "Industry": "Software Development",
                "noEmployees": "500-1000",
                "formationYear": "2005",
                "type": "Private Company"
            }
        ],
        "url": "https://example.com/candidates/john-smith"
    },
    {
        "candidate_id": "C002",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "overall_score": "78.3",
        "match_details": [
            {
                "name": "Skills Match",
                "score": 22,
                "max_score": 30,
                "overview": "Good technical foundation with room for growth"
            },
            {
                "name": "Experience Match",
                "score": 24,
                "max_score": 30,
                "overview": "Solid experience in related fields"
            },
            {
                "name": "Education Match",
                "score": 16,
                "max_score": 20,
                "overview": "Relevant educational background"
            }
        ],
        "company_bg_details": [
            {
                "company": "Global Software Solutions",
                "Industry": "Enterprise Software",
                "noEmployees": "5000-10000",
                "formationYear": "1990",
                "type": "Public Corporation"
            },
            {
                "company": "StartUp Tech",
                "Industry": "Mobile Applications",
                "noEmployees": "50-200",
                "formationYear": "2015",
                "type": "Startup"
            }
        ],
        "url": "https://example.com/candidates/sarah-johnson"
    }
]

# Streamlit UI
st.title("Top Candidates for Job ID")

# Input for Job ID
job_id_input = st.text_input("Enter Job ID", placeholder="Enter a number")

if st.button("Fetch Candidates"):
    if job_id_input.isdigit():  # Check if the input is numeric
        # Using dummy data instead of API call
        candidates = dummy_candidates

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

                # Create an expander for each candidate
                with st.expander(f"📋 {first_name} {last_name} - Score: {overall_score}", expanded=True):
                    # Basic info section
                    st.markdown(f"**🆔 Candidate ID:** {candidate_id}")

                    # Match percentages section
                    st.markdown("### 📊 Match Analysis")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Skills Match", f"{skill_percentage:.1f}%")
                    with col2:
                        st.metric("Experience Match", f"{experience_percentage:.1f}%")
                    with col3:
                        st.metric("Education Match", f"{education_percentage:.1f}%")

                    # Company background section
                    st.markdown("### 🏢 Company Background")
                    if company_bg_details:
                        for company in company_bg_details:
                            with st.container():
                                st.markdown(f"""
                                * **Company:** {company['company']}
                                * **Industry:** {company['Industry']}
                                * **Size:** {company['noEmployees']} employees
                                * **Founded:** {company['formationYear']}
                                * **Type:** {company['type']}
                                """)
                                st.markdown("---")
                    else:
                        st.markdown("No company background details available.")

                    # Profile link
                    st.markdown(f"**🔗 Profile:** [View Complete Profile]({candidate['url']})")

        else:
            st.write("No candidates found for the given Job ID.")
    else:
        st.error("Please enter a valid numeric Job ID.")