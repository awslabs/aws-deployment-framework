const express = require('express');

const app = express()

app.set('view engine', 'ejs');
app.use(express.static('public'))

app.get('/', (req, res) => {
    res.render('index', {
        region: process.env.REGION,
        environment: process.env.ENVIRONMENT
    })
})

app.get('/version', (req, res) => {
    res.json({"version": "0.0.1"})
})

app.listen(3000, () => {
    console.log('Listening on 3000')
})