import aioconsole
import asyncio
import click
import re
from server.chat_server import ChatServer
from client.chat_client import (
    ChatClient,
    NotConnectedError,
    LoginConflictError,
    LoginError,
    RoomConflictError,
    RoomLoginError,
    JoinResponseError,
    LeaveResponseError,
    MessagePostError
)

async def display_msgs(chat_client):
    while True:
        msg = await chat_client.get_user_msg()
        print('\n\n\t\tRECEIVED MESSAGE: {}'.format(msg))


async def handle_user_input(chat_client, loop):
    while True:
        print('\n\n')
        print('< 1 > closes connection and quits')
        print('< 2 > list logged-in users')
        print('< 3 > login')
        print('< 4 > list rooms')
        print('< 5 > post message to public room')
        print('< 6 > create private room')
        print('< 7 > join private room')
        print('< 8 > leave room')
        print('< 9 > direct message')
        print('< 10 > post message to private room')

        print('\tchoice: ', end='', flush=True)

        command = await aioconsole.ainput()
        # 1- closes connection and quits
        if command == '1':
            # disconnect
            try:
                chat_client.disconnect()
                print('disconnected')
                loop.stop()
                break
            except NotConnectedError:
                print('client is not connected ...')
            except Exception as e:
                print('error disconnecting {}'.format(e))

        # 2- list logged-in users
        elif command == '2':  # list registered users
            users = await chat_client.lru()
            print('logged-in users: {}'.format(', '.join(users)))

        # 3- login
        elif command == '3':
            login_name = await aioconsole.ainput('enter login-name: ')
            try:
                await chat_client.login(login_name)
                print(f'logged-in as {login_name}')

            except LoginConflictError:
                print('login name already exists, pick another name')
            except LoginError:
                print('error loggining in, try again')

        # 4- list rooms
        elif command == '4':
            try:
                rooms = await chat_client.lrooms()
                for room in rooms:
                    print('\n\t\troom name ({}), owner ({}): {}'.format(room['name'], room['owner'], room['description']))

            except Exception as e:
                print('error getting rooms from server {}'.format(e))

        # 5- post message to public room
        elif command == '5':
            try:
                user_message = await aioconsole.ainput('enter your message: ')
                await chat_client.post(user_message, 'public')

            except RoomLoginError:
                print("Error posting message to room. Please login and try again.")

            except MessagePostError:
                print("Error posting message to room. Please join room and try again.")

            except Exception as e:
                print('error posting message {}'.format(e))

        # 6- create private room
        elif command == '6':
            try:
                room_name = await aioconsole.ainput('enter a room name: ')
                while (len(room_name) > 10) or (not re.match("^[A-Za-z0-9]*$", room_name)):  # regex check works, len does not
                    print('Error: room name must be 10 characters or less and cannot contain any special characters.')
                    room_name = await aioconsole.ainput('enter a room name: ')
                description = await aioconsole.ainput('enter the room description: ')
                response = await chat_client.add_private_room(room_name, description)
                if response.strip() == "success":
                    print("created room")

            except RoomConflictError:
                print("Error creating private room. Room already exists.")

            except RoomLoginError:
                print("Error creating private room. Please login and try again.")

            except Exception as e:
                print("error creating private room")
                print(e)

        # 7- join private room
        elif command == '7':
            try:
                room_to_join = await aioconsole.ainput('enter the private room name: ')
                response = await chat_client.join_private_room(room_to_join)
                if response == 'joined':
                    print('room joined')

            except RoomLoginError:
                print("Error joining private room. Please login and try again.")

            except JoinResponseError:
                print('Error joining private room -- room does not exist. Please try again with a valid room name.')

        # 8- leave a room
        elif command == '8':
            try:
                room_to_leave = await aioconsole.ainput('enter the name of the room to leave: ')
                response = await chat_client.leave_private_room(room_to_leave)
                if response == 'left':
                    print('you have left {}'.format(room_to_leave)) # fixed parentheses

            except RoomLoginError:
                print("Error creating leaving private room. Please login and try again.")

            except LeaveResponseError:
                print('Error leaving private room -- room does not exist or you are not a member.\n' +
                      'Please try again with a valid room name')

        # 9- direct message
        elif command == '9':
            try:
                user = await aioconsole.ainput('enter the user to send the message to: ')
                message = await aioconsole.ainput('enter the message to send: ')
                response = await chat_client.direct_message(user, message)
                if response.strip() == "success":
                    print('Successfully sent DM to {}.'.format(user))

            except MessagePostError:
                print('No user "{}" exists. Please try again with a valid username.'.format(user))

            except LoginError:
                print('Error sending direct message. Please login and try again.')

            except Exception as e:
                print("Error sending message to user.")
                print(e)

        # 10 - message to private room
        elif command == '10':
            try:
                user_message = await aioconsole.ainput('enter your message: ')
                room_name = await aioconsole.ainput('enter the room name: ')
                await chat_client.post(user_message, room_name)

            except RoomLoginError:
                print("Error posting message to room. Please login and try again.")

            except MessagePostError:
                print("Error posting message to room. Please join room and try again.")

            except Exception as e:
                print('Error posting message {} to {} room'.format(user_message, room_name))
                print(e)


@click.group()
def cli():
    pass


@cli.command(help="run chat client")
# @click.argument("host")
@click.argument("port", type=int)
def connect(port):
    chat_client = ChatClient(port=port)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(chat_client._connect())

    # display menu, wait for command from user, invoke method on client
    asyncio.ensure_future(handle_user_input(chat_client=chat_client, loop=loop))
    asyncio.ensure_future(display_msgs(chat_client=chat_client))

    loop.run_forever()


@cli.command(help='run chat server')
@click.argument('port', type=int)
def listen(port):
    click.echo('starting chat server at {}'.format(port))
    chat_server = ChatServer(port=port)
    chat_server.start()


if __name__ == '__main__':
    cli()