1) Clone
git clone <your-repo-url>
cd Frontend

2) Prerequisites

Node.js 18+ or 20+

npm, pnpm, or yarn

Check:

node -v
npm -v

3) Install
# pick one
npm install
# pnpm install
# yarn install

4) Environment

Create Frontend/.env.local. Point it to the backend (default per backend README: http://127.0.0.1:8001).

If unsure which framework you use, set all three keys.

# .env.local

# Vite
VITE_API_BASE_URL=http://127.0.0.1:8001

# Next.js
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001

# Create React App
REACT_APP_API_BASE_URL=http://127.0.0.1:8001

4) Run

Start the backend first, then start the frontend:

# use the script that exists in package.json
npm run dev
# or
npm start

