# Security Dashboard

A comprehensive real-time security system monitoring dashboard built with Next.js, TypeScript, and Tailwind CSS.

## Features

- **User Authentication**: Secure login and signup pages with JWT-based authentication
- **Live Feed Monitoring**: Real-time camera feeds with online/offline status
- **Event Database**: Complete event log with severity levels and timestamps
- **Dashboard Overview**: Key metrics and system status at a glance
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark Theme**: Professional dark UI optimized for security monitoring

## Project Structure

```
Interface@SENTINEL/
├── app/
│   ├── api/                 # API routes
│   │   ├── auth/           # Authentication endpoints
│   │   ├── dashboard/      # Dashboard statistics
│   │   ├── feeds/          # Live feed data
│   │   └── database/       # Event records
│   ├── auth/               # Auth pages
│   │   ├── login/
│   │   └── signup/
│   ├── dashboard/          # Dashboard pages
│   │   ├── feeds/
│   │   ├── database/
│   │   └── settings/
│   ├── components/         # Reusable components
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── lib/                    # Utilities
├── public/                 # Static assets
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── .eslintrc.json
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

4. Create an account or login with demo credentials

## Available Pages

### Authentication
- `/auth/login` - User login
- `/auth/signup` - User registration

### Dashboard
- `/dashboard` - Main overview with statistics and recent activity
- `/dashboard/feeds` - Live camera feeds monitoring
- `/dashboard/database` - Event log and history
- `/dashboard/settings` - User preferences and settings

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User registration

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics

### Feeds
- `GET /api/feeds` - Get all live feeds

### Database
- `GET /api/database/records` - Get event records

## Technologies Used

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Authentication**: JWT (mock implementation)
- **State Management**: React hooks

## Development

### Build for production:
```bash
npm run build
npm start
```

### Run linter:
```bash
npm run lint
```

## Future Enhancements

- Real database integration (PostgreSQL/MongoDB)
- WebSocket support for real-time updates
- Advanced search and filtering
- User role management
- Email notifications
- Two-factor authentication
- Detailed analytics and reporting
- Camera recording and playback

## Notes

- This is a frontend/mock backend implementation
- User data is stored in memory (not persistent)
- For production, integrate with a real database and authentication service
- Replace mock API responses with actual backend services

## License

MIT
