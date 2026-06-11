import os
import aiohttp
import tempfile
import math

from PIL import Image
from PIL import ImageSequence

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register


@register("gifhelper", "QuanWenG", "GIF倍速插件", "1.0.0")
class MyPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("倍速")
    async def gifSpeed(self, event: AstrMessageEvent):

        parts = event.get_message_str().split()

        if len(parts) < 2:
            yield event.plain_result(
                "用法：回复GIF后发送\n/倍速 2"
            )
            return

        try:
            speed = float(parts[1])

            if speed <= 0:
                raise ValueError()

        except ValueError:
            yield event.plain_result("倍速必须大于0")
            return

        reply = None

        for seg in event.get_messages():
            if seg.__class__.__name__ == "Reply":
                reply = seg
                break

        if not reply:
            yield event.plain_result("请回复GIF使用")
            return

        image = None

        for item in reply.chain:
            if item.__class__.__name__ == "Image":
                image = item
                break

        if not image:
            yield event.plain_result("引用消息中没有图片")
            return

        url = image.url

        with tempfile.TemporaryDirectory() as tmpdir:

            input_path = os.path.join(tmpdir, "input.gif")
            output_path = os.path.join(tmpdir, "output.gif")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:

                    if resp.status != 200:
                        yield event.plain_result("下载GIF失败")
                        return

                    with open(input_path, "wb") as f:
                        f.write(await resp.read())

            try:

                gif = Image.open(input_path)

                raw_frames = []
                raw_durations = []

                for frame in ImageSequence.Iterator(gif):

                    raw_frames.append(
                        frame.copy().convert("RGBA")
                    )

                    raw_durations.append(
                        frame.info.get("duration", 100)
                    )

                if not raw_frames:
                    raise Exception("GIF没有帧")

                frames = []
                durations = []

                for frame, duration in zip(raw_frames, raw_durations):

                    frames.append(frame)

                    durations.append(
                        max(
                            10,
                            int(duration / speed)
                        )
                    )

                # 如果所有帧都触底10ms
                # 再删帧
                if speed > 1 and all(d <= 10 for d in durations):

                    skip = math.ceil(speed)

                    frames = frames[::skip]
                    durations = durations[::skip]

                frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=0,
                    disposal=2,
                    optimize=False,
                )

            except Exception as e:

                yield event.plain_result(
                    f"GIF处理失败：{e}"
                )
                return

            yield event.image_result(output_path)