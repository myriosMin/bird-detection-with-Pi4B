/*-------------- SCROLL TO TOP --------------*/
const scrollToTopBtn = document.getElementById('scrollToTopBtn');
window.onscroll = function() { scrollFunction(); };
function scrollFunction() {
  if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
    scrollToTopBtn.style.display = 'block';
  } else {
    scrollToTopBtn.style.display = 'none';
  }
}
scrollToTopBtn.addEventListener('click', function() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
});

/*-------------- ULTRASONIC SLIDER --------------*/
function updateDistanceSlider() {
  const slider = document.getElementById('distanceSlider');
  const distanceValue = document.getElementById('distanceValue');

  // Update displayed radius percentage (0-100%)
  const percentage = parseFloat(slider.value);
  distanceValue.textContent = percentage.toFixed(2) + "%";

  // Send updated percentage to Flask (0-100 range)
  fetch('/api/update_radius', {  // Fixed route
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ radius: percentage }) // Sending as 0-100
  })
  .then(response => response.json())
  .then(data => console.log("Updated Radius:", data.new_radius, "(User input %:", data.user_display_value, ")"))
  .catch(error => console.error("Error updating radius:", error));
}

/*-------------- SOUND SLIDER --------------*/
function updateFreqSlider() {
  const freqSlider = document.getElementById('freqSlider');
  const freqValue = document.getElementById('freqValue');

  // Convert slider value (0-100) to actual Hz range (1500-2300)
  const percentage = parseFloat(freqSlider.value);
  freqValue.textContent = percentage + " kHz";

  // Send updated frequency percentage to Flask
  fetch('/api/update_buzzer_pitch', {  // Fixed API route
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pitch: percentage }) // Sending as 0-100%
  })
  .then(response => response.json())
  .then(data => console.log("Updated Buzzer Pitch:", data.new_pitch, "(User input %:", data.user_display_value, ")"))
  .catch(error => console.error("Error updating buzzer pitch:", error));
}

/*-------------- DETERRENT STATUS TOGGLE --------------*/
function toggleDeterrentStatus() {
  const deterrentStatusElement = document.getElementById('deterrentStatus');
  const isCurrentlyActive = deterrentStatusElement.textContent === "ON";

  // Toggle status
  const newStatus = !isCurrentlyActive; // Toggle true/false
  deterrentStatusElement.textContent = newStatus ? "ON" : "OFF";

  // Send updated deterrent status to Flask
  fetch('/api/update_deterrent_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  })
  .then(response => response.json())
  .then(data => console.log("Updated Deterrent Status:", data.new_status))
  .catch(error => console.error("Error updating deterrent status:", error));
}

/*-------------- ACCORDION --------------*/
const accordionToggles = document.querySelectorAll('.accordion-toggle');
accordionToggles.forEach(toggle => {
  toggle.addEventListener('click', () => {
    toggle.classList.toggle('active');
    const content = toggle.nextElementSibling;
    if (content.style.maxHeight) {
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
    }
  });
});

/*-------------- MODAL --------------*/
function openModal(modalId) {
  document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside of it
window.onclick = function(event) {
  const ultrasonicModal = document.getElementById('ultrasonicModal');
  const soundModal = document.getElementById('soundModal');

  if (event.target === ultrasonicModal) {
    ultrasonicModal.style.display = 'none';
  }
  if (event.target === soundModal) {
    soundModal.style.display = 'none';
  }
};

/*-------------- CHATBOT LOGIC --------------*/
function toggleChatWindow() {
  const chatWindow = document.getElementById('chatWindow');
  chatWindow.style.display = (chatWindow.style.display === 'flex') ? 'none' : 'flex';
}

function handleEnter(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
}

function getBotResponse(userMessage) {
  const msg = userMessage.toLowerCase();

  // 1) Greeting / Basic
  if (msg.includes('hello') || msg.includes('hi')) {
    return (
      "Hello there! I'm here to answer questions about our bird detection & deterrent system. " +
      "How can I help you today?"
    );
  }

  // 2) Project Objective
  if (msg.includes('objective') || msg.includes('purpose')) {
    return (
      "Our main objective is to provide a humane, eco-friendly way to monitor and deter birds in " +
      "sensitive areas without harming them. By combining a Raspberry Pi 4, Arduino, and sensor technology, " +
      "we collect real-time data, reduce damage, and protect local wildlife."
    );
  }

  // 3) Detection (Ultrasonic, Sensors)
  if (
    msg.includes('ultrasonic') ||
    msg.includes('sensor') ||
    msg.includes('detect') ||
    (msg.includes('how') && msg.includes('detect'))
  ) {
    return (
      "We use ultrasonic sensors connected to a Raspberry Pi 4 and Arduino to detect birds within a specified range. " +
      "This allows real-time, accurate distance measurements without harming the animals."
    );
  }

  // 4) Deterrent (Sound, Range, Threshold)
  if (
    msg.includes('deter') ||
    msg.includes('deterrent') ||
    msg.includes('sound') ||
    (msg.includes('how') && msg.includes('deter'))
  ) {
    return (
      "Once birds are detected within a threshold, the system triggers a gentle, customizable ultrasonic or audible sound. " +
      "The goal is to deter birds without physical interaction or harm, maintaining a safe distance."
    );
  }

  // 5) Dashboard / Configuration
  if (
    msg.includes('dashboard') ||
    msg.includes('configure') ||
    msg.includes('sound profile') ||
    msg.includes('volume') ||
    msg.includes('range')
  ) {
    return (
      "Our dashboard lets you configure detection ranges, sound profiles, and volume levels. " +
      "You can also monitor real-time data and logs to track bird activity and system performance."
    );
  }

  // 6) Hardware (Raspberry Pi, Arduino)
  if (msg.includes('raspberry pi') || msg.includes('arduino') || msg.includes('hardware')) {
    return (
      "Our system uses a Raspberry Pi 4 and Arduino working together. " +
      "The Raspberry Pi handles data logging and dashboard functionality, " +
      "while the Arduino focuses on sensor data (like ultrasonic readings)."
    );
  }

  // 7) Thank-you
  if (msg.includes('thank')) {
    return (
      "You're most welcome! Is there anything else you'd like to know about the system?"
    );
  }

  // 8) Fallback: Not sure
  return (
    "I'm not entirely sure what you mean. Here are some topics I can help with:\n" +
    "• Objective or purpose of this project\n" +
    "• How detection works (ultrasonic sensors)\n" +
    "• How deterrent sound works\n" +
    "• Configuring the dashboard (range, volume, logs)\n\n" +
    "Try asking: “How does the ultrasonic sensor detect birds?” or “What is the project objective?”"
  );
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  const chatBody = document.getElementById('chatBody');
  const userMessage = input.value.trim();

  if (!userMessage) return;

  // Show user message
  chatBody.innerHTML += `<div class="user-msg">${userMessage}</div>`;
  input.value = '';
  chatBody.scrollTop = chatBody.scrollHeight;

  // Generate bot response
  const botReply = getBotResponse(userMessage);
  chatBody.innerHTML += `<div class="bot-msg">${botReply}</div>`;
  chatBody.scrollTop = chatBody.scrollHeight;
}

/*-------------- FILTER CARDS --------------*/
function filterCards() {
  const searchInput = document.getElementById('searchInput');
  const filterValue = searchInput.value.toLowerCase();
  const cards = document.querySelectorAll('.card');
  cards.forEach(card => {
    const sensorType = card.getAttribute('data-sensor');
    if (sensorType.toLowerCase().includes(filterValue) || filterValue === '') {
      card.style.display = 'block';
    } else {
      card.style.display = 'none';
    }
  });
}

/*-------------- CHART --------------*/
let birdActivityChart;
window.onload = function() {
  // Initialize Chart.js chart
  const ctx = document.getElementById('birdActivityChart').getContext('2d');
  birdActivityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['10s ago','8s ago','6s ago','4s ago','2s ago','Now'],
      datasets: [
        {
          label: 'Inside Area',
          data: [0, 2, 1, 3, 2, 4],  // Placeholder, will be replaced by real data
          backgroundColor: 'rgba(182, 215, 168, 0.2)',  // Same color as large birds
          borderColor: '#b6d7a8',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
        },
        {
          label: 'Outside Area',
          data: [2, 1, 3, 1, 4, 2],  // Placeholder, will be replaced by real data
          backgroundColor: 'rgba(237, 106, 90, 0.2)',  // Same color as small birds
          borderColor: '#ed6a5a',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Number of Birds Detected'
          }
        }
      },
      responsive: true,
      maintainAspectRatio: false,
    }
  });

  // Start loading real-time data updates for the chart
  fetchBirdActivityData();
};

function fetchBirdActivityData() {
  fetch('/api/bird_activity')
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        console.error("Failed to fetch bird activity data:", data.error);
        return;
      }

      // Update chart labels (timestamps)
      birdActivityChart.data.labels = data.timestamps.map(timestamp => {
        const timeObj = new Date(timestamp);
        return timeObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      });

      // Update chart data (bird counts)
      birdActivityChart.data.datasets[0].data = data.inside_birds;  // Inside detection area
      birdActivityChart.data.datasets[1].data = data.outside_birds; // Outside detection area

      birdActivityChart.update(); // Refresh chart
    })
    .catch(error => console.error("Error fetching bird activity:", error));
}

// Call this function every 10 seconds to update the chart dynamically
setInterval(fetchBirdActivityData, 10000);

/*-------------- DOWNLOAD CSV --------------*/
document.getElementById("downloadCsvBtn").addEventListener("click", function() {
    window.location.href = "/download_csv";  // Redirects to the download endpoint
});

/* ---------------------- Real-Time Notifications ---------------------- */
const socket = io();

// Listen for bird alert events from Flask-SocketIO
socket.on('bird_alert', (data) => {
    console.log("Notification received:", data.message);
    showBirdAlert(data.message);
});

function showBirdAlert(message) {
    const alertBox = document.createElement('div');
    alertBox.className = "bird-alert";
    alertBox.innerHTML = `
        <strong>?? Alert:</strong> ${message}
        <button onclick="this.parentElement.style.display='none'">Dismiss</button>
    `;
    
    document.body.appendChild(alertBox);
    setTimeout(() => {
        alertBox.style.display = "none";
    }, 10000);  // Hide after 10 seconds
}
