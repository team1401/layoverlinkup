const express = require('express');
const bodyParser = require('body-parser');
const { Pool } = require('pg');
const app = express();
const port = process.env.PORT || 3000;

app.set('view engine', 'ejs');
app.use(bodyParser.urlencoded({ extended: false }));
app.use(express.static('public'));

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgres://user:password@localhost/connectfly'
});

// Pages
app.get('/', (req, res) => {
  res.render('index');
});

app.get('/register', (req, res) => {
  res.render('register');
});

// Users
app.post('/register', async (req, res) => {
  const { name, email, homeAirport } = req.body;
  try {
    const result = await pool.query('INSERT INTO users(name, email, home_airport) VALUES($1, $2, $3) RETURNING id', [name, email, homeAirport]);
    res.send(`Registered with id ${result.rows[0].id}`);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error registering user');
  }
});

// Itineraries
app.get('/itineraries/new', (req, res) => {
  res.render('itinerary');
});

app.post('/itineraries', async (req, res) => {
  const { userId, airline, flightNumber, departAirport, arrivalAirport, departTime, arrivalTime, layoverAirport, layoverStart, layoverEnd } = req.body;
  try {
    await pool.query(`INSERT INTO itineraries(user_id, airline, flight_number, depart_airport, arrival_airport, depart_time, arrival_time, layover_airport, layover_start, layover_end) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
      [userId, airline, flightNumber, departAirport, arrivalAirport, departTime, arrivalTime, layoverAirport, layoverStart, layoverEnd]);
    res.send('Itinerary added');
  } catch (err) {
    console.error(err);
    res.status(500).send('Error adding itinerary');
  }
});

// Groups
app.get('/groups/new', (req, res) => {
  res.render('group');
});

app.post('/groups', async (req, res) => {
  const { name } = req.body;
  try {
    const result = await pool.query('INSERT INTO groups(name) VALUES($1) RETURNING id', [name]);
    res.send(`Created group ${result.rows[0].id}`);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error creating group');
  }
});

app.post('/groups/:groupId/users', async (req, res) => {
  const { groupId } = req.params;
  const { userId } = req.body;
  try {
    await pool.query('INSERT INTO group_users(group_id, user_id) VALUES($1,$2)', [groupId, userId]);
    res.send('Added to group');
  } catch (err) {
    console.error(err);
    res.status(500).send('Error adding user to group');
  }
});

// Match detection
async function getMatches(groupId) {
  const query = `SELECT i1.user_id as user1, i2.user_id as user2, i1.layover_airport, 
    GREATEST(i1.layover_start, i2.layover_start) as overlap_start,
    LEAST(i1.layover_end, i2.layover_end) as overlap_end
    FROM itineraries i1
    JOIN itineraries i2 ON i1.layover_airport = i2.layover_airport AND i1.user_id <> i2.user_id
    JOIN group_users gu1 ON gu1.user_id = i1.user_id
    JOIN group_users gu2 ON gu2.user_id = i2.user_id AND gu1.group_id = gu2.group_id
    WHERE gu1.group_id = $1 AND i1.layover_end > i2.layover_start AND i2.layover_end > i1.layover_start`;
  const { rows } = await pool.query(query, [groupId]);
  return rows.map(r => ({
    user1: r.user1,
    user2: r.user2,
    airport: r.layover_airport,
    start: r.overlap_start,
    end: r.overlap_end
  }));
}

app.get('/groups/:groupId/matches', async (req, res) => {
  try {
    const matches = await getMatches(req.params.groupId);
    res.render('matches', { matches });
  } catch (err) {
    console.error(err);
    res.status(500).send('Error finding matches');
  }
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
