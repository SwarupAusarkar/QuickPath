async function shortenUrl() {
      const originalUrl = document.getElementById('long-url').value.trim();
      const customShort = document.getElementById('custom-url').value.trim();
      const resultDiv = document.getElementById('result');
      const errorDiv = document.getElementById('error');

      resultDiv.innerHTML = '';
      errorDiv.innerHTML = '';

      if (!originalUrl) {
        errorDiv.textContent = 'Please enter a long URL';
        return;
      }

      try {
        const response = await fetch('http://localhost:8000/shorten', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            original_url: originalUrl,
            custom_short: customShort === '' ? null : customShort
          })
        });

        const data = await response.json();

        if (!response.ok) {
          errorDiv.textContent = data.detail || 'Something went wrong';
        } else {
          resultDiv.innerHTML = `
            <p class="text-green-400 font-semibold">Shortened URL:</p>
            <a href="${data.short_url}" target="_blank" class="underline text-indigo-400">${data.short_url}</a>
          `;
        }
      } catch (err) {
        errorDiv.textContent = 'Failed to connect to the server';
      }
    }