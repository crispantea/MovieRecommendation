# Frontend Application

The frontend consists of a React + Vite application that talks to the Flask backend (API).

## Setup

1. Install dependencies
    ```bash
    npm install
    ```

2. Set the necessary environment variables (reference: [`.env.example`](.env.example)) and export it:
    ```bash
    set -a
    source .env
    set +a
    ```

3. Start the dev server
    ```bash
    npm run dev
    ```

## Configuration

The backend URL is set in `src/api/auth.js`:
```js
const API_URL = 'http://localhost:3000'
```

## Project Structure

```
├── eslint.config.js    # Linting rules
├── index.html          # HTML entry point, loads main.jsx
├── node_modules        # Installed dependencies
│   ├── ...
├── package.json        # Project metadata, scripts, dependencies
├── package-lock.json   # Locked dependency versions
├── public              # Static assets served as-is
│   ├── ...
├── README.md           # Project documentation
├── src
│   ├── api             # Backend request functions
│   │   └── ...
│   ├── components      # Reusable UI components
│   │   └── ...
│   ├── hooks           # Custom React hooks (state/logic)
│   │   └── ...
│   ├── App.jsx         # Root component
│   └── main.jsx        # React entry point, mounts App to the DOM
└── vite.config.js      # Vite configuration
```