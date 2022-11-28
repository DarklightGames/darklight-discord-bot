import asyncio
import netstruct

from typing import Iterable


PAYLOAD = b"\x80\x00\x00\x00\x00"


class QueryProtocol(asyncio.Protocol):
    def __init__(self, message, on_con_lost) -> None:
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None
        self.data = b''

    def connection_made(self, transport) -> None:
        self.transport = transport
        self.transport.sendto(self.message)

    def datagram_received(self, data, addr) -> None:
        self.data = data
        self.transport.close()

    def error_received(self, exc) -> None:
        print('Error received:', exc)

    def connection_lost(self, exc) -> None:
        try:
            self.on_con_lost.set_result(True)
        except asyncio.exceptions.InvalidStateError:
            pass


class ServerInfo:
    def __init__(self, addr: tuple[str, int], query_data):
        self.addr = addr
        self.query_data = query_data
        self.data = []
        self.name = ''
        self.map = ''
        self.players = 0
        self.max_players = 0

        if len(query_data) > 0:
            self.data = netstruct.unpack(b'<ciciiib$b$b$ii', query_data)
            self.name = ' '.join(self.data[6].decode('latin-1').split())[:-1]
            self.map = self.data[7].decode('latin-1').replace('\xc2\xa0', ' ')[:-1]
            self.players = self.data[9]
            self.max_players = self.data[10]


async def query(addr: tuple[str, int]) -> ServerInfo | None:
    loop = asyncio.get_event_loop()
    on_con_lost = loop.create_future()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: QueryProtocol(PAYLOAD, on_con_lost),
        remote_addr=addr)

    try:
        await asyncio.wait_for(on_con_lost, 0.2)
    except asyncio.TimeoutError:
        pass
    finally:
        transport.close()

    if protocol.data:
        return ServerInfo(addr, protocol.data)


async def get(*args: tuple[str, int]) -> Iterable[ServerInfo | None]:
    queryTasks = [query(addr) for addr in args]
    return await asyncio.gather(*queryTasks)
