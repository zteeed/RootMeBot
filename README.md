# RootMeBot

## Add it to your discord server

Follow [this link](https://discordapp.com/api/oauth2/authorize?client_id=523372231561314304&permissions=8&scope=bot)

## Self deployment

```bash
docker-compose up -d
```

It is not possible to mount a VOLUME with Dockerfile specifying both source and destination, so i choose to use docker-compose to make it possible.
