from watmon_service.db.models import (
    DeviceDB,
    NodeDB,
    VertexpoolDB,
    Device_LabelDB,
    Vertexpool_LabelDB,
)
from typing import Callable, Awaitable, AsyncGenerator
from watmon_service.db.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from contextlib import _AsyncGeneratorContextManager
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from watmon_service.schema import Label, DevicePost
from watmon_service.db.session import session_generate
from fastapi import Request


class VertexpoolManager:
    """Respsposible for WATMON datasebase interections and triggering callbacks when an update occurs."""

    def __init__(self, session_manager: Callable[[], _AsyncGeneratorContextManager[AsyncSession]]):
        self.generate_session = session_manager
        self.trigger_callables: list[Callable] = []
        self.async_trigger_callables: list[Callable[..., Awaitable[None]]] = []

    async def _trigger_callables(self, log_msg: str | None = None):
        for callable in self.trigger_callables:
            callable(log_msg=log_msg)
        for callable in self.async_trigger_callables:
            await callable(log_msg=log_msg)

    def construct_labels(self, labels: list[Label]) -> list[Device_LabelDB]:
        device_labels = []
        for label in labels:
            label.label_key
            device_labels.append(Device_LabelDB(key=label.label_key, value=label.label_value))
        return device_labels

    async def add_node(self, nodename: str, ip: str, vertexpool_id: int | None = None) -> NodeDB:
        async with self.generate_session() as session:
            try:
                node = NodeDB(nodename=nodename, vertexpool_id=vertexpool_id, ip=ip)
                await self._ensure_vertexpool(target=node, session=session)
                session.add(node)
                await session.commit()
                await self._trigger_callables("node added")
                return node
            except IntegrityError as e:
                await session.rollback()
                print("Integrity Error:", str(e))
                raise HTTPException(status_code=409, detail="nodename already exists")
            except Exception as e:
                await session.rollback()
                print("Error:", str(e))

    async def add_device(self, dev: DevicePost) -> DeviceDB:
        async with self.generate_session() as session:
            try:
                device = DeviceDB(
                    device_id=dev.id,
                    devicename=dev.name,
                    ip=dev.ip,
                    vertexpool_id=dev.vertexpool_id,
                )
                device.labels = self.construct_labels(dev.labels)
                await self._ensure_vertexpool(target=device, session=session)
                session.add(device)
                await session.commit()
                await self._trigger_callables("device added")
                return device
            except IntegrityError as e:
                await session.rollback()
                print("Integrity Error:", str(e))
                raise HTTPException(status_code=409, detail="device id already exists")
            except Exception as e:
                await session.rollback()
                print("Error:", str(e))

    async def _ensure_vertexpool(self, target: NodeDB | DeviceDB, session: AsyncSession):
        """Ensures that given vertexpool_id exists in vertexpool table when inserting a Node or Device

        If no vertexpool_id specified for Node|Device creates one."""

        if not target.vertexpool_id:
            # no vertexpool_id given
            new_vertexpool = VertexpoolDB()
            if isinstance(target, NodeDB):
                new_vertexpool.nodes.append(target)
            elif isinstance(target, DeviceDB):
                new_vertexpool.devices.append(target)
            session.add(new_vertexpool)
        else:
            result = await session.execute(select(VertexpoolDB).where(VertexpoolDB.id == target.vertexpool_id))
            if not result.scalars().all():
                # given vertexpool_id does not exist
                new_vertexpool = VertexpoolDB(id=target.vertexpool_id)
                session.add(new_vertexpool)

    async def get_device(self, device_id: int) -> DeviceDB | None:
        "GET device by device_id , returns None if id not found"
        async with self.generate_session() as session:
            res = await session.execute(
                select(DeviceDB)
                .where(DeviceDB.device_id == device_id)
                .options(selectinload(DeviceDB.labels))
                .options(selectinload(DeviceDB.vertexpool))
            )
            return res.scalar_one_or_none()

    async def get_node(self, nodename: str) -> NodeDB | None:
        async with self.generate_session() as session:
            res = await session.execute(select(NodeDB).where(NodeDB.nodename == nodename))
            return res.scalar_one_or_none()

    async def get_vertexpool(self, vertexpool_id) -> VertexpoolDB | None:
        "GET vertexpool by vertexpool_id , returns None if id not found"
        async with self.generate_session() as session:
            result = await session.execute(
                select(VertexpoolDB)
                .where(VertexpoolDB.id == vertexpool_id)
                .options(selectinload(VertexpoolDB.nodes))
                .options(selectinload(VertexpoolDB.labels))
                .options(selectinload(VertexpoolDB.devices).selectinload(DeviceDB.labels))
            )
            return result.scalar_one_or_none()

    async def update_device_ip(self, device_id: int, new_device_ip: str) -> DeviceDB:
        async with self.generate_session() as session:
            device = await self.get_device(device_id)
            if not device:
                raise HTTPException(status_code=404, detail="device id not found")
            device.ip = new_device_ip
            session.add(device)
            await session.commit()
            await self._trigger_callables(log_msg="device ip updated")
            return await self.get_device(device_id)

    async def patch_device(
        self,
        device_id: int,
        name: str | None = None,
        labels: list[Label] | None = None,
        ip: str | None = None,
    ):
        async with self.generate_session() as session:
            call_trigger = False
            device = await self.get_device(device_id)
            if not device:
                raise HTTPException(status_code=404, detail="device id not found")
            if name:
                device.devicename = name
            if labels:
                dev_labels = [
                    Device_LabelDB(
                        key=label.label_key,
                        value=label.label_value,
                        device_id=device_id,
                    )
                    for label in labels
                ]
                device.labels = dev_labels
            else:
                device.labels = labels
            if ip:
                device.ip = ip
                call_trigger = True
            session.add(device)
            await session.commit()
            if call_trigger:
                await self._trigger_callables("device ip patched")
            return await self.get_device(device_id)

    async def patch_node(self, nodename, ip: str | None = None):
        async with self.generate_session() as session:
            node = await self.get_node(nodename)
            if not node:
                raise HTTPException(status_code=404, detail="nodename not found")
            if ip:
                node.ip = ip
            session.add(node)
            await session.commit()
            await self._trigger_callables("node patched")
            return await self.get_node(nodename)

    async def patch_vertexpool_labels(self, vertexpool_id: int, labels: list[Label] | None = None):
        async with self.generate_session() as session:
            vertexpool = await self.get_vertexpool(vertexpool_id)
            if not vertexpool:
                raise HTTPException(status_code=404, detail="vertexpool id not found")
            if labels:
                vertexpool_labels = [
                    Vertexpool_LabelDB(
                        key=label.label_key,
                        value=label.label_value,
                        vertexpool_id=vertexpool_id,
                    )
                    for label in labels
                ]
                vertexpool.labels = vertexpool_labels
            else:
                vertexpool.labels = []
            session.add(vertexpool)
            await session.commit()
            return await self.get_vertexpool(vertexpool_id)

    async def _edit_vertexes(self, vertex: NodeDB | DeviceDB, new_vertexpool_id: int, session: AsyncSession):
        old_vertexpool = vertex.vertexpool
        try:
            if new_vertexpool_id is not None:
                result = await session.execute(select(VertexpoolDB).filter_by(id=new_vertexpool_id))
                existing_vertexpool = result.scalar_one_or_none()
                if existing_vertexpool:
                    vertex.vertexpool_id = new_vertexpool_id
                else:
                    new_vertexpool = VertexpoolDB(id=new_vertexpool_id)
                    session.add(new_vertexpool)
                    vertex.vertexpool_id = new_vertexpool_id
            else:
                # if new_vertexpool_id is None, we create a new vertexpool
                new_vertexpool = VertexpoolDB()
                if isinstance(vertex, NodeDB):
                    new_vertexpool.nodes.append(vertex)
                elif isinstance(vertex, DeviceDB):
                    new_vertexpool.devices.append(vertex)
                session.add(new_vertexpool)
                vertex.vertexpool_id = new_vertexpool.id

            await session.commit()
            await self._check_if_vertexpool_is_orphaned(old_vertexpool, session)
            await self._trigger_callables("vertexpool_id edited")
        except Exception as e:
            await session.rollback()
            print("Error:", str(e))

    async def move_node_to_vertexpool(self, nodename: str, new_vertexpool_id: int | None = None):
        async with self.generate_session() as session:
            result = await session.execute(
                select(NodeDB).where(NodeDB.nodename == nodename).options(selectinload(NodeDB.vertexpool))
            )
            node = result.scalar_one_or_none()
            if not node:
                raise HTTPException(status_code=404, detail="Node not found")
            await self._edit_vertexes(node, new_vertexpool_id, session)

    async def move_device_to_vertexpool(self, device_id: int, new_vertexpool_id: int | None = None):
        async with self.generate_session() as session:
            result = await session.execute(
                select(DeviceDB).where(DeviceDB.device_id == device_id).options(selectinload(DeviceDB.vertexpool))
            )
            device = result.scalar_one_or_none()
            if not device:
                raise HTTPException(status_code=404, detail="device not found")
            await self._edit_vertexes(device, new_vertexpool_id, session)

    async def delete_node(self, nodename):
        async with self.generate_session() as session:
            try:
                result = await session.execute(
                    select(NodeDB).where(NodeDB.nodename == nodename).options(selectinload(NodeDB.vertexpool))
                )
                node = result.scalar_one_or_none()
                if node:
                    await session.delete(node)
                    await session.commit()
                    await self._check_if_vertexpool_is_orphaned(node.vertexpool, session)
                    await self._trigger_callables("node deleted")
            except Exception as e:
                await session.rollback()
                print("Error:", str(e))

    async def delete_device(self, device_id):
        async with self.generate_session() as session:
            try:
                result = await session.execute(
                    select(DeviceDB).where(DeviceDB.device_id == device_id).options(selectinload(DeviceDB.vertexpool))
                )
                device = result.scalar_one_or_none()
                if device:
                    await session.delete(device)
                    await session.commit()
                    await self._check_if_vertexpool_is_orphaned(device.vertexpool, session)
                    await self._trigger_callables("device deleted")
            except Exception as e:
                await session.rollback()
                print("Error:", str(e))

    async def _check_if_vertexpool_is_orphaned(self, vertexpool: VertexpoolDB, session: AsyncSession):
        result = await session.execute(
            select(VertexpoolDB)
            .where(VertexpoolDB.id == vertexpool.id)
            .options(selectinload(VertexpoolDB.nodes))
            .options(selectinload(VertexpoolDB.devices))
        )
        full_vertexpool = result.scalars().one_or_none()
        if full_vertexpool and (not full_vertexpool.nodes and not full_vertexpool.devices):
            await session.delete(full_vertexpool)
            await session.commit()

    async def get_nodes(
        self,
    ) -> list[NodeDB]:
        "Retuns all nodes"
        async with self.generate_session() as session:
            result = await session.execute(select(NodeDB))
            return result.scalars().all()

    async def get_devices(
        self,
    ) -> list[DeviceDB]:
        async with self.generate_session() as session:
            result = await session.execute(
                select(DeviceDB).options(selectinload(DeviceDB.labels)).options(selectinload(DeviceDB.vertexpool))
            )
            return result.scalars().all()

    async def get_vertexpools(self) -> list[VertexpoolDB]:
        async with self.generate_session() as session:
            result = await session.execute(
                select(VertexpoolDB)
                .options(selectinload(VertexpoolDB.nodes))
                .options(selectinload(VertexpoolDB.labels))
                .options(selectinload(VertexpoolDB.devices).selectinload(DeviceDB.labels))
            )
            return result.scalars().all()

    async def delete_dev_label(self, key: str, value: str, device_id: int):
        async with self.generate_session() as session:
            res = await session.execute(
                select(Device_LabelDB).where(
                    Device_LabelDB.device_id == device_id,
                    Device_LabelDB.key == key,
                    Device_LabelDB.value == value,
                )
            )
            label = res.scalar_one_or_none()
            if label:
                await session.delete(label)
                await session.commit()

    async def add_device_label(self, device_id: int, label_key: str, label_value: str) -> DeviceDB:
        async with self.generate_session() as session:
            dev = await self.get_device(device_id=device_id)
            if dev:
                label = Device_LabelDB(key=label_key, value=label_value, device_id=device_id)
                dev.labels.append(label)
                session.add(dev)
                await session.commit()
                return dev
            raise HTTPException(status_code=404, detail="Device not found")

    async def add_vertexpool_label(self, vertexpool_id: int, label_key: str, label_value: str) -> DeviceDB:
        async with self.generate_session() as session:
            vertexpool = await self.get_vertexpool(vertexpool_id)
            if vertexpool:
                label = Vertexpool_LabelDB(key=label_key, value=label_value, vertexpool_id=vertexpool_id)
                vertexpool.labels.append(label)
                session.add(vertexpool)
                await session.commit()
                return vertexpool
            raise HTTPException(status_code=404, detail="Vertexpool not found")

    async def close(self):
        async with self.generate_session() as session:
            await session.close()


async def get_vertexpool_manager(
    request: Request,
) -> AsyncGenerator[VertexpoolManager, None]:
    """Dependency to get VertexpoolManager instance with new session, also registers async trigger callables from the app state."""
    vertexpool_manager = VertexpoolManager(session_manager=session_generate)
    vertexpool_manager.async_trigger_callables.append(request.app.state.agent_updater.trigger)
    try:
        yield vertexpool_manager
    finally:
        await vertexpool_manager.close()
