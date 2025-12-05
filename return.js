// mock-server.js
const express = require('express')
const app = express()
app.use(express.json())
app.post('/login', (req, res) => {
  const { username } = req.body
  if (!username) return res.status(400).json({ message: 'Missing username' })
  return res.json({ access_token: `mock-token-for-${username}` })
})
app.listen(8081, () => console.log('Mock server on http://localhost:8081'))
