import asyncio
import sys

from ecactusecos.ecactusecos import EcactusEcos


async def main(username: str, password: str):
    # Create a new client by supplying username and password
    ecactusecos = EcactusEcos(username, password)

    # Authenticate the client by attempting to login
    # On success, the user id and authentication are set on the client
    await ecactusecos.authenticate()
    print("Auth token: %s" % ecactusecos._auth_token)

    # Fetch the customer information
    await ecactusecos.customer_overview()
    print("Customer ID: %s" % ecactusecos.get_customer_info())

    # Fetch the devices of the customer
    await ecactusecos.device_overview()
    print("Devices: %s" % ecactusecos._devices)

    # # Request all actual energy consumption rates of the sources which correspond to the configured
    # # source_types, by default equal to DEFAULT_SOURCE_TYPES in const.py.
    actuals = await ecactusecos.actuals()
    print("Actuals: %s" % actuals)

    # current_measurements() is a utility method which combines all steps above and only returns
    # the current values for each source, omitting the historical values.
    current_measurements = await ecactusecos.current_measurements()
    print("Current measurements: %s" % current_measurements)

    # # Manually logout the client.
    ecactusecos.invalidate_authentication()


if __name__ == "__main__":
    if len(sys.argv) - 1 == 2:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(sys.argv[1], sys.argv[2]))
    else:
        print("python example.py <username> <password>")
