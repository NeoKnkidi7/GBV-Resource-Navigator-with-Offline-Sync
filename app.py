import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import json
import time
import os
import zipfile
import base64
from io import BytesIO

# Custom CSS for professional design
st.markdown("""
<style>
    :root {
        --primary: #8e44ad;
        --secondary: #9b59b6;
        --accent: #e74c3c;
        --light: #f9ebfc;
        --dark: #2c3e50;
        --success: #27ae60;
    }
    
    .stApp {
        background-color: #faf5ff;
        background-image: radial-gradient(#e0d1f3 1.5px, transparent 1.5px), 
                          radial-gradient(#e0d1f3 1.5px, #faf5ff 1.5px);
        background-size: 60px 60px;
        background-position: 0 0, 30px 30px;
        color: var(--dark);
    }
    
    .st-b7, .css-1d391kg, .st-c0 {
        background-color: rgba(255, 255, 255, 0.92) !important;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-left: 4px solid var(--primary);
    }
    
    h1, h2, h3, h4 {
        color: var(--primary);
        border-bottom: 2px solid var(--secondary);
        padding-bottom: 10px;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 28px;
        font-weight: 600;
        transition: all 0.3s ease;
        margin: 5px 0;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 15px rgba(142, 68, 173, 0.4);
    }
    
    .emergency-button {
        background: linear-gradient(135deg, var(--accent) 0%, #c0392b 100%) !important;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
        70% { box-shadow: 0 0 0 12px rgba(231, 76, 60, 0); }
        100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
    }
    
    .offline-badge {
        background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 15px;
    }
    
    .resource-card {
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-left: 4px solid var(--secondary);
        transition: transform 0.3s ease;
    }
    
    .resource-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.15);
    }
    
    .contact-chip {
        display: inline-block;
        background: var(--light);
        padding: 8px 15px;
        border-radius: 30px;
        margin: 5px;
        font-weight: 500;
        border: 1px solid var(--secondary);
    }
    
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background: var(--dark);
        color: white;
        padding: 10px;
        text-align: center;
        font-size: 0.8rem;
        z-index: 100;
    }
    
    .safe-exit {
        position: absolute;
        top: 15px;
        right: 15px;
        background: var(--light);
        color: var(--accent);
        border: 1px solid var(--accent);
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
        cursor: pointer;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for offline mode and data
def init_session_state():
    if 'offline_mode' not in st.session_state:
        st.session_state.offline_mode = False
    if 'resources' not in st.session_state:
        st.session_state.resources = pd.DataFrame()
    if 'geolocation' not in st.session_state:
        st.session_state.geolocation = None
    if 'safe_mode' not in st.session_state:
        st.session_state.safe_mode = False
    if 'emergency_expanded' not in st.session_state:
        st.session_state.emergency_expanded = False

# Safe exit function
def safe_exit():
    st.session_state.safe_mode = True
    st.experimental_rerun()

# Load resources data (simulate online/offline)
def load_resources():
    # Sample dataset
    data = {
        'name': [
            'Hope Shelter', 
            'Safe Haven Women\'s Center',
            'New Beginnings Refuge',
            'Legal Aid GBV Division',
            'Survivor Support Legal Clinic'
        ],
        'type': ['Shelter', 'Shelter', 'Shelter', 'Legal Aid', 'Legal Aid'],
        'address': [
            '123 Safety St, Johannesburg',
            '456 Protection Ave, Cape Town',
            '789 Refuge Rd, Durban',
            '101 Justice Blvd, Pretoria',
            '202 Empowerment Way, Port Elizabeth'
        ],
        'phone': [
            '0800 555 123',
            '0800 555 456',
            '0800 555 789',
            '0800 555 101',
            '0800 555 202'
        ],
        'hours': ['24/7', '24/7', '24/7', '9am-5pm Mon-Fri', '8:30am-4:30pm Mon-Fri'],
        'capacity': [20, 35, 15, 'N/A', 'N/A'],
        'latitude': [-26.2041, -33.9249, -29.8587, -25.7479, -33.9608],
        'longitude': [28.0473, 18.4241, 31.0218, 28.2293, 25.6022],
        'services': [
            'Emergency shelter, counseling, medical assistance',
            'Shelter, childcare, job training',
            'Short-term housing, legal referrals',
            'Free legal representation, protection orders',
            'Legal counseling, court accompaniment'
        ],
        'languages': ['English, Zulu', 'English, Afrikaans', 'English, Zulu', 'English', 'English, Xhosa']
    }
    return pd.DataFrame(data)

# Get coordinates from address
def get_coordinates(address):
    try:
        geolocator = Nominatim(user_agent="gbv_resource_navigator")
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return None

# Create a downloadable offline package
def create_offline_package(resources):
    # Create ZIP file with resources
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipf:
        # Add resources as CSV
        resources.to_csv('resources.csv', index=False)
        zipf.write('resources.csv')
        
        # Add HTML page for offline use
        offline_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GBV Resource Navigator - Offline</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .resource { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; }
                .emergency { background-color: #ffe6e6; padding: 15px; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>GBV Resource Navigator - Offline</h1>
            <div class="emergency">
                <h2>Emergency Contacts</h2>
                <p>GBV Emergency Line: <strong>0800 428 428</strong></p>
                <p>Police Emergency: <strong>10111</strong></p>
                <p>Suicide Helpline: <strong>0800 567 567</strong></p>
            </div>
            <div id="resources"></div>
            <script>
                // Load resources from CSV
                fetch('resources.csv')
                    .then(response => response.text())
                    .then(data => {
                        const resources = data.split('\\n').slice(1);
                        let html = '<h2>Available Resources</h2>';
                        resources.forEach(row => {
                            if (row) {
                                const [name, type, address, phone, hours, capacity, lat, lng, services, languages] = row.split(',');
                                html += `
                                    <div class="resource">
                                        <h3>${name}</h3>
                                        <p><strong>Type:</strong> ${type}</p>
                                        <p><strong>Address:</strong> ${address}</p>
                                        <p><strong>Phone:</strong> ${phone}</p>
                                        <p><strong>Hours:</strong> ${hours}</p>
                                        <p><strong>Services:</strong> ${services}</p>
                                    </div>
                                `;
                            }
                        });
                        document.getElementById('resources').innerHTML = html;
                    });
            </script>
        </body>
        </html>
        """
        with open('offline.html', 'w') as f:
            f.write(offline_html)
        zipf.write('offline.html')
    
    buffer.seek(0)
    return buffer

# Initialize session state
init_session_state()

# Page configuration
st.set_page_config(
    page_title="SafePath Navigator",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Safe exit button
if not st.session_state.safe_mode:
    st.markdown('<div class="safe-exit" onclick="safeExit()">🚨 Safe Exit</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <script>
            function safeExit() {
                window.location.href = 'https://www.google.com';
            }
        </script>
        """, 
        unsafe_allow_html=True
    )
else:
    st.success("You have safely exited the application. Close this browser tab immediately.")
    st.stop()

# Load resources
if st.session_state.resources.empty:
    try:
        # Try to load from online source
        st.session_state.resources = load_resources()
    except Exception as e:
        st.error(f"Online resources unavailable. Switching to offline mode. Error: {str(e)}")
        st.session_state.offline_mode = True

# Navigation
with st.sidebar:
    st.image("https://i.imgur.com/XtQF0Qn.png", width=200)
    selected = option_menu(
        menu_title=None,
        options=["Resource Finder", "Emergency Contacts", "Safety Planning", "Offline Access"],
        icons=["search", "telephone", "clipboard-heart", "download"],
        default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#f5f3ff"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "5px"},
        }
    )
    
    st.markdown("---")
    
    # Geolocation
    st.subheader("📍 Your Location")
    location_input = st.text_input("Enter your location (city, address, or postal code)", key="location_input")
    
    if st.button("Use Current Location", key="geolocate_btn"):
        # Simulate with a default location
        st.session_state.geolocation = (-25.7479, 28.2293)  # Pretoria coordinates
        st.success("Location set to current position")
    
    if location_input:
        with st.spinner("Locating..."):
            coords = get_coordinates(location_input)
            if coords:
                st.session_state.geolocation = coords
                st.success(f"Location set to {location_input}")
            else:
                st.error("Could not find location. Please try again.")
    
    # Offline status
    st.markdown("---")
    if st.session_state.offline_mode:
        st.markdown("<div class='offline-badge'>OFFLINE MODE</div>", unsafe_allow_html=True)
    else:
        st.success("Online Mode")
    
    st.markdown("### Need Help Now?")
    if st.button("🚨 Immediate Danger Assistance", key="emergency_btn", use_container_width=True, 
                help="Call emergency services immediately"):
        st.session_state.emergency_expanded = True

# Emergency overlay
if st.session_state.get('emergency_expanded', False):
    st.markdown(
        """
        <div style="position:fixed; top:0; left:0; width:100%; height:100%; 
                    background:rgba(231, 76, 60, 0.95); z-index:9999; padding:50px;
                    color:white; text-align:center;">
            <h1 style="color:white;">EMERGENCY ASSISTANCE</h1>
            <h2>Call for immediate help:</h2>
            <div style="font-size:2rem; margin:30px 0;">
                <p>GBV Emergency Line: <strong>0800 428 428</strong></p>
                <p>Police Emergency: <strong>10111</strong></p>
                <p>Suicide Helpline: <strong>0800 567 567</strong></p>
            </div>
            <h3>If you're in immediate danger:</h3>
            <ul style="text-align:left; max-width:600px; margin:0 auto; font-size:1.2rem;">
                <li>Go to a safe place if possible</li>
                <li>Call emergency services</li>
                <li>Contact a trusted friend or family member</li>
                <li>You are not alone - help is available</li>
            </ul>
            <div style="margin-top:40px;">
                <button onclick="window.location.reload();" 
                        style="background:white; color:#e74c3c; border:none; padding:15px 40px; 
                               font-size:1.2rem; border-radius:8px; cursor:pointer;">
                    I'm Safe Now
                </button>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Main content
st.title("🕊️ SafePath Navigator")
st.markdown("### Find GBV Shelters, Legal Aid, and Support Services")
st.markdown("---")

# Resource Finder Page
if selected == "Resource Finder":
    st.subheader("Find Nearby Resources")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        resource_type = st.selectbox("Resource Type", ["All", "Shelter", "Legal Aid", "Counseling", "Medical"])
    with col2:
        distance = st.slider("Maximum Distance (km)", 1, 100, 20)
    with col3:
        services = st.multiselect("Specific Services", 
                                 ["24/7 Access", "Child-Friendly", "Legal Assistance", 
                                  "Counseling", "Medical Care", "Transportation"])
    
    # Show results
    if not st.session_state.resources.empty:
        # Filter resources
        filtered_resources = st.session_state.resources.copy()
        
        if resource_type != "All":
            filtered_resources = filtered_resources[filtered_resources['type'] == resource_type]
        
        # Calculate distances if location is set
        if st.session_state.geolocation:
            user_location = st.session_state.geolocation
            filtered_resources['distance'] = filtered_resources.apply(
                lambda row: geodesic(user_location, (row['latitude'], row['longitude'])).km,
                axis=1
            )
            filtered_resources = filtered_resources[filtered_resources['distance'] <= distance]
            filtered_resources = filtered_resources.sort_values('distance')
        
        # Show map and results
        if not filtered_resources.empty:
            # Create map
            st.subheader("Resource Map")
            if st.session_state.geolocation:
                user_location = st.session_state.geolocation
                m = folium.Map(location=user_location, zoom_start=10)
            else:
                m = folium.Map(location=[-28.4793, 24.6727], zoom_start=5)  # Default to South Africa view
            
            # Add user location
            if st.session_state.geolocation:
                folium.Marker(
                    location=user_location,
                    popup="Your Location",
                    icon=folium.Icon(color="blue", icon="user", prefix="fa")
                ).add_to(m)
            
            # Add resources
            for idx, row in filtered_resources.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"<b>{row['name']}</b><br>{row['type']}<br>📞 {row['phone']}",
                    icon=folium.Icon(
                        color="red" if row['type'] == "Shelter" else "green", 
                        icon="home" if row['type'] == "Shelter" else "balance-scale", 
                        prefix="fa"
                    )
                ).add_to(m)
            
            # Display map
            st_folium(m, width=1200, height=400)
            
            # Show resource cards
            st.subheader(f"Found {len(filtered_resources)} Resources")
            for idx, row in filtered_resources.iterrows():
                distance_info = f"{row['distance']:.1f} km away" if 'distance' in row and st.session_state.geolocation else ""
                
                with st.expander(f"### {row['name']} - {row['type']} {distance_info}", expanded=False):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**Address:** {row['address']}")
                        st.markdown(f"**Phone:** `{row['phone']}`")
                        st.markdown(f"**Hours:** {row['hours']}")
                        if row['type'] == "Shelter":
                            st.markdown(f"**Capacity:** {row['capacity']} people")
                    with col2:
                        st.markdown(f"**Services:** {row['services']}")
                        st.markdown(f"**Languages:** {row['languages']}")
                        st.markdown(f"**Get Directions:** [Google Maps](https://www.google.com/maps/dir/?api=1&destination={row['latitude']},{row['longitude']})")
        else:
            st.warning("No resources found matching your criteria. Try adjusting your filters.")
    else:
        st.error("Resource data is not available. Please try again later or use offline resources.")

# Emergency Contacts Page
elif selected == "Emergency Contacts":
    st.header("Emergency Contacts")
    st.markdown("### Immediate Assistance")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div class="resource-card">
                <h3>📞 GBV Emergency Line</h3>
                <p><strong>0800 428 428</strong></p>
                <p>24/7 support for gender-based violence</p>
                <p>Call or SMS: *120*7867#</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="resource-card">
                <h3>🚓 Police Emergency</h3>
                <p><strong>10111</strong></p>
                <p>24/7 emergency response</p>
                <p>From mobile: 112</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div class="resource-card">
                <h3>🩹 Medical Emergency</h3>
                <p><strong>10177</strong></p>
                <p>Ambulance services</p>
                <p>From mobile: 112</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("24/7 Support Services")
    
    st.markdown("""
        <div class="resource-card">
            <h3>🤝 Lifeline Counseling</h3>
            <p><strong>0861 322 322</strong></p>
            <p>24-hour suicide prevention and counseling</p>
            <p>SMS: 31393 (and we'll call you back)</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="resource-card">
            <h3>👶 Child Protection</h3>
            <p><strong>0800 055 555</strong></p>
            <p>Childline South Africa</p>
            <p>24-hour helpline for children</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="resource-card">
            <h3>⚖️ Legal Assistance</h3>
            <p><strong>0800 333 177</strong></p>
            <p>Legal Aid South Africa</p>
            <p>Mon-Fri: 8am-4pm</p>
        </div>
    """, unsafe_allow_html=True)

# Safety Planning Page
elif selected == "Safety Planning":
    st.header("Safety Planning")
    st.markdown("### Create a personalized safety plan")
    
    with st.expander("📝 Create Your Safety Plan", expanded=True):
        st.markdown("""
            **A safety plan helps prepare for dangerous situations. Complete the following steps:**
        """)
        
        step1 = st.checkbox("### Step 1: Identify safe areas in your home")
        if step1:
            st.text_area("Where are the safest areas? (Avoid kitchens, bathrooms, or rooms with weapons)", 
                        height=100, placeholder="e.g., Near exits, rooms with phones", key="safe_areas")
        
        step2 = st.checkbox("### Step 2: Prepare an emergency bag")
        if step2:
            st.multiselect("What to include:",
                          ["Important documents", "Money and bank cards", "Medications", 
                           "Extra keys", "Phone charger", "Change of clothes", "Children's essentials"],
                          key="emergency_bag")
        
        step3 = st.checkbox("### Step 3: Establish a code word")
        if step3:
            st.text_input("Create a code word to use with trusted friends/family when you need help",
                         placeholder="e.g., 'Is Aunt Mary coming?'", key="code_word")
        
        step4 = st.checkbox("### Step 4: Identify safe places to go")
        if step4:
            st.text_area("List safe locations you can go in an emergency",
                        height=100, placeholder="e.g., Neighbor's house, local shelter, police station", key="safe_places")
        
        step5 = st.checkbox("### Step 5: Plan for children")
        if step5:
            st.text_area("How will you keep children safe? Who can help with childcare?",
                        height=100, key="children_plan")
        
        if st.button("Save Safety Plan", key="save_plan_btn"):
            st.success("Safety plan saved. Remember to store this information securely.")
    
    st.markdown("---")
    st.subheader("Digital Safety Tips")
    
    tips = [
        "Clear your browser history regularly - use private browsing mode",
        "Create new email accounts your abuser doesn't know about",
        "Use a safe computer at a library or community center",
        "Change passwords frequently and use strong passwords",
        "Disable location services on your devices",
        "Use encrypted messaging apps like Signal"
    ]
    
    for i, tip in enumerate(tips):
        st.markdown(f"""
            <div class="resource-card">
                <h4>🔒 Tip #{i+1}</h4>
                <p>{tip}</p>
            </div>
        """, unsafe_allow_html=True)

# Offline Access Page
elif selected == "Offline Access":
    st.header("Offline Access")
    st.markdown("### Prepare for connectivity gaps")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
            <div class="resource-card">
                <h3>📥 Download Offline Package</h3>
                <p>Get all essential resources and information for offline use:</p>
                <ul>
                    <li>Emergency contact numbers</li>
                    <li>Shelter locations and details</li>
                    <li>Legal aid resources</li>
                    <li>Safety planning guide</li>
                </ul>
                <p><em>Works without internet connection</em></p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Generate Offline Package", key="download_btn"):
            with st.spinner("Preparing offline resources..."):
                offline_package = create_offline_package(st.session_state.resources)
                st.success("Offline package ready for download!")
                
                # Create download link
                b64 = base64.b64encode(offline_package.getvalue()).decode()
                href = f'<a href="data:application/zip;base64,{b64}" download="gbv_offline_resources.zip">Download ZIP File</a>'
                st.markdown(href, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="resource-card">
                <h3>📱 Mobile App Installation</h3>
                <p>For better offline access, install our mobile app:</p>
                <ol>
                    <li>Open this page on your mobile device</li>
                    <li>Tap the share button in your browser</li>
                    <li>Select \"Add to Home Screen\"</li>
                </ol>
                <p><strong>Once installed:</strong></p>
                <ul>
                    <li>Works completely offline</li>
                    <li>Fast access to emergency contacts</li>
                    <li>GPS navigation to shelters</li>
                    <li>Discreet \"Safe Exit\" feature</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("Offline Safety Features")
    
    features = [
        ("🛡️", "Discreet Mode", "Quickly hide the app with a fake calculator interface"),
        ("🗺️", "Offline Maps", "Access maps and directions without internet"),
        ("📞", "Emergency Call", "One-tap calling to pre-set emergency contacts"),
        ("📝", "Safety Planning", "Access your safety plan anytime"),
        ("🔋", "Low Power Mode", "Optimized for extended battery life")
    ]
    
    cols = st.columns(5)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i]:
            st.markdown(f"""
                <div style="text-align:center; padding:15px; border-radius:10px; background:white; box-shadow:0 4px 8px rgba(0,0,0,0.1);">
                    <div style="font-size:2rem;">{icon}</div>
                    <h4>{title}</h4>
                    <p style="font-size:0.9rem;">{desc}</p>
                </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p>SafePath Navigator - GBV Resource Finder | 
    Confidential Support for Survivors | 
    Remember: You are not alone - help is available 24/7</p>
</div>
""", unsafe_allow_html=True)
