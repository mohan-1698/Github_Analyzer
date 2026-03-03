# GitHub Analyzer Frontend

A modern, futuristic React application for analyzing your GitHub profile with AI-powered insights.

## 🎨 Features

✨ **Modern UI with Framer Motion Animations**
- Smooth page transitions and component animations
- Glassmorphism effects for premium look
- Animated gradient backgrounds
- Micro-interactions on hover

📊 **Interactive Charts & Metrics**
- Commit activity line chart
- Language distribution pie chart
- Productivity, consistency, and impact scores
- Real-time metric counters

🤖 **AI-Powered Insights**
- Google Gemini integration for smart recommendations
- Personalized developer insights
- Behavioral pattern analysis

🔐 **Secure GitHub OAuth**
- GitHub OAuth 2.0 authentication
- JWT token management
- Secure session handling

## 🚀 Getting Started

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

1. **Install dependencies:**
```bash
npm install
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Configure environment variables:**
```env
VITE_API_URL=http://localhost:8000
VITE_GITHUB_CLIENT_ID=your_github_app_client_id
VITE_GITHUB_REDIRECT_URI=http://localhost:3000/login
```

### Development

```bash
npm run dev
```

The app will run on `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Navbar.jsx      # Navigation bar
│   ├── ProfileCard.jsx # User profile display
│   ├── ScoreCard.jsx   # Animated metric cards
│   ├── CommitChart.jsx # Commit activity chart
│   ├── LanguageChart.jsx # Language distribution
│   ├── InsightsPanel.jsx # AI insights display
│   └── LoadingAnimation.jsx # Skeleton loaders
├── pages/              # Page components
│   ├── LoginPage.jsx   # GitHub OAuth login
│   ├── DashboardPage.jsx # Main dashboard
│   └── LoadingPage.jsx # Loading screen
├── hooks/              # Custom React hooks
│   ├── useAuth.js      # Authentication logic
│   └── useDashboard.js # Dashboard data fetching
├── utils/              # Utility functions
│   ├── api.js          # API client with axios
│   └── constants.js    # App constants
├── App.jsx             # Main app component
├── main.jsx            # Entry point
└── index.css           # Global styles & animations
```

## 🎬 Animation Features

### Page Transitions
- Fade in on load
- Slide up from bottom
- Smooth route transitions

### Component Animations
- Hover scale effects
- Glow effects on interactive elements
- Floating background particles
- Animated gradient shifts
- Pulse effects on metrics

### Chart Animations
- Smooth data point transitions
- Animated bar/line drawing
- Interactive hover tooltips
- Smooth axis updates

## 🔗 API Integration

The app connects to your backend at `http://localhost:8000`:

```javascript
// Endpoints
GET  /auth/github                    // Get auth URL
GET  /auth/github/callback?code=...  // OAuth callback
GET  /github/sync                    // Sync GitHub data
GET  /analytics/calculate            // Calculate metrics
GET  /insights/generate              // Generate AI insights
GET  /dashboard/data                 // Get dashboard data
```

## 📦 Dependencies

- **react** - UI library
- **react-router-dom** - Client-side routing
- **framer-motion** - Animation library
- **recharts** - Data visualization
- **tailwindcss** - Utility-first CSS
- **axios** - HTTP client
- **lucide-react** - Icon library

## 🎨 Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:
```javascript
colors: {
  'primary': '#0f172a',
  'secondary': '#1e293b',
  'accent': '#3b82f6',
}
```

### Animations
Modify animation timing in `index.css`:
```css
@keyframes gradientShift {
  0% { backgroundPosition: 0% 50%; }
  50% { backgroundPosition: 100% 50%; }
  100% { backgroundPosition: 0% 50%; }
}
```

## 🔐 Security

- Tokens stored in localStorage (consider migration to httpOnly cookies for production)
- CORS proxy for API calls
- Secure OAuth flow
- Input validation on all forms

## 📱 Responsive Design

- Mobile-first approach
- Tailwind responsive utilities
- Adaptive layouts for all screen sizes
- Touch-friendly interactive elements

## 🐛 Troubleshooting

### Port 3000 already in use?
```bash
npm run dev -- --port 3001
```

### API calls failing?
- Ensure backend is running on port 8000
- Check VITE_API_URL in .env
- Verify GitHub OAuth credentials

### Animations lagging?
- Check browser DevTools Performance tab
- Reduce animation duration in constants.js
- Use Chrome/Firefox for best performance

## 📝 License

This project is part of GitHub Analyzer suite.

## 🙋 Support

For issues or questions, check the main project repository.
