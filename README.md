# 🔗 QuickPath - Modern URL Shortener

A lightning-fast, feature-rich URL shortening service with beautiful UI and powerful QR code integration.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyourusername%2FQuickPath)

## ✨ Features

- **Instant URL Shortening** - Create short, memorable links in seconds
- **Custom Short URLs** - Choose your own custom shortcodes
- **QR Code Generation** - Every short link comes with a downloadable QR code
- **Beautiful UI** - Clean, responsive design with light/dark mode
- **Fast Redirects** - Lightning-fast redirects to the original URL
- **API Access** - Full-featured API for integration with your applications

## 🚀 Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQL with SQLAlchemy ORM
- **QR Storage**: Supabase Storage
- **Frontend**: HTML/CSS/JS with Tailwind CSS
- **Deployment**: Vercel-ready

## 🖥️ Screenshots

<div align="center">
  <img src="assets\Screenshot 2025-04-19 011559.png" alt="Light Mode" width="45%" />
  <img src="assets\Screenshot 2025-04-19 011611.png" alt="Dark Mode" width="45%" />
</div>

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- A Supabase account (for QR code storage)
- A PostgreSQL database

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DATABASE_URL=postgresql://user:password@localhost/dbname
SUPABASE_URL=your_supabase_url
SUPABASE_API_KEY=your_supabase_api_key
BASE_URL=http://localhost:8000 or Vercel deployed domain
```

### Local Development

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/QuickPath.git
   cd QuickPath
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a Supabase storage bucket named `qr-codes`

5. Run the development server
   ```bash
   uvicorn main:app --reload
   ```

6. Open http://localhost:8000 in your browser

## 🌐 Deployment

### Vercel Deployment

This project is optimized for Vercel deployment:

1. Fork this repository
2. Connect your fork to Vercel
3. Set up the environment variables in the Vercel dashboard
4. Deploy!

### Other Platforms

The application can be deployed to any platform that supports Python:

1. Clone the repository
2. Install dependencies with `pip install -r requirements.txt`
3. Set environment variables
4. Run with a production ASGI server like Uvicorn or Gunicorn

## 📝 API Documentation

### Shorten URL

```
POST /shorten
```

Request body:
```json
{
  "original_url": "https://example.com/very/long/url/that/needs/shortening",
  "custom_short": "custom"  // Optional
}
```

Response:
```json
{
  "original_url": "https://example.com/very/long/url/that/needs/shortening",
  "short_url": "https://shortrive.com/custom",
  "qr_code_url": "https://shortrive.com/qr/custom.png"
}
```

### Redirect

```
GET /{short_url}
```

Redirects to the original URL.

## 🧩 Project Structure

```
├── .env                  # Environment variables (not in repository)
├── .gitignore            # Git ignore file
├── database.py           # Database models and connections
├── database_manager.py   # URL and QR code management logic
├── main.py               # FastAPI application entry point
├── requirements.txt      # Python dependencies
├── static/               # Static files
│   └── index.html        # Frontend UI
└── vercel.json           # Vercel deployment configuration
```

## 🛣️ Roadmap

- [ ] Analytics dashboard for link statistics
- [ ] User authentication for managing links
- [ ] Link expiration and password protection
- [ ] Browser extensions
- [ ] Mobile apps

### 📫 Let's Connect!

<p align="center">
  <a href="https://www.linkedin.com/in/swarup-ausarkar/"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white"/></a>
  <a href="https://www.instagram.com/swarup_ausarkar145/"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white"/></a>
  <a href="mailto:ausarkarswarup@gmail.com"><img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white"/></a>
</p>

### ✅ Support This Project

If you find this project useful, please consider:

- ⭐ Starring it on GitHub
- 🍴 Forking it for your own projects
- 🐛 Submitting issues or pull requests
- 💬 Sharing feedback and suggestions

I'm always looking to improve and expand this project. If you have ideas or want to collaborate, don't hesitate to reach out!