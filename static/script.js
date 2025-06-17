async function login() {
  const username = document.getElementById('login-username')?.value.trim();
  const password = document.getElementById('login-password')?.value.trim();
  const error = document.getElementById('login-message');

  if (!error) return; 
  error.textContent = '';

  if (!username || !password) {
    error.textContent = 'Please enter both username and password.';
    return;
  }

  try {
    const res = await axios.post('http://localhost:5000/login', {
      username: username,
      password: password
    });

    if (res.status === 200) {
      window.location.href = '/home';
    }
  } catch (err) {
    if (err.response && err.response.status === 401) {
      error.textContent = 'Invalid username or password, try again.';
    } else {
      error.textContent = 'Something went wrong. Please try again.';
      console.log('Login error:', err);
    }
  }
}

async function signup() {
  const username = document.getElementById('signup-username')?.value.trim();
  const password = document.getElementById('signup-password')?.value.trim();
  const error = document.getElementById('signup-message');

  if (!error) return;
  error.textContent = '';

  if (username.length < 8) {
    error.textContent = 'Username must be at least 8 characters long.';
    return;
  } else if (username.length > 20) {
    error.textContent = 'Username must be at most 20 characters long.';
    return;
  }

  if (password.length < 8) {
    error.textContent = 'Password must be at least 8 characters long.';
    return;
  }

  try {
    const res = await axios.post('http://localhost:5000/signup', {
      username: username,
      password: password
    });

    if (res.status === 201) {
      window.location.href = '/';
    }
  } catch (err) {
    if (err.response && err.response.status === 400) {
      error.textContent = 'Username already exists, please choose another one.';
    } else {
      error.textContent = 'Something went wrong. Please try again.';
    }
  }
}

async function getRecommendations() {
  const title = document.getElementById('movieInput')?.value.trim();
  const countValue = document.getElementById('countInput')?.value;
  const count = parseInt(countValue);
  const errorDiv = document.getElementById('error');
  if (!errorDiv) return;
  errorDiv.textContent = '';

  if (!title) {
    errorDiv.textContent = 'Please enter a movie title.';
    return;
  }

  if (isNaN(count) || count < 1) {
    errorDiv.textContent = 'Please enter a number greater than 0 for recommendations.';
    return;
  }

  try {
    const response = await axios.get(`http://127.0.0.1:5000/recommend?title=${encodeURIComponent(title)}&num=${count}`);
    const results = response.data;

    const list = document.getElementById('results');
    const suggestionsDiv = document.getElementById('suggestions');
    if (!list || !suggestionsDiv) return;

    list.innerHTML = '';
    suggestionsDiv.innerHTML = '';

    if (!results.length) {
      errorDiv.textContent = 'No recommendations found for this movie.';
      return;
    }

    results.forEach(movie => {
      const li = document.createElement('li');
      li.textContent = movie;
      list.appendChild(li);
    });
  } catch (error) {
    errorDiv.textContent = 'Something went wrong. Please try again.';
  }
}

async function fetchSuggestions(query) {
  const list = document.getElementById('suggestions');
  if (!list || !query) {
    if (list) list.innerHTML = '';
    return;
  }

  try {
    const response = await axios.get(`http://127.0.0.1:5000/autocomplete?q=${encodeURIComponent(query)}`);
    const suggestions = response.data;

    list.innerHTML = '';
    if (suggestions.length === 0) {
      const li = document.createElement('li');
      li.textContent = 'No suggestions found';
      li.style.fontStyle = 'italic';
      list.appendChild(li);
      return;
    }

    suggestions.forEach(suggestion => {
      const li = document.createElement('li');
      li.textContent = suggestion;
      li.style.cursor = 'pointer';
      li.onclick = () => {
        const input = document.getElementById('movieInput');
        if (input) input.value = suggestion;
        list.innerHTML = '';
      };
      list.appendChild(li);
    });
  } catch (error) {
    list.innerHTML = '';
  }
}

window.onload = function () {
  const movieInput = document.getElementById('movieInput');
  const recommendBtn = document.getElementById('recommendBtn');

  if (movieInput) {
    movieInput.addEventListener('input', (e) => {
      fetchSuggestions(e.target.value);
    });
  }

  if (recommendBtn) {
    recommendBtn.addEventListener('click', getRecommendations);
  }
};
