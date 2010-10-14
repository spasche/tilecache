import os
import sys
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

__all__ = ['ImageMergeMerger', 'PILMerger']

class ImageMerger:
    def __init__ (self, service):
        self.service = service

class ImageMergeMerger(ImageMerger):
    @staticmethod
    def available():
        if "TC_NO_IMAGE_MERGE" in os.environ:
            return False
        try:
            import image_merge
        except ImportError:
            return False
        return True

    def merge(self, tiles, params):
        import image_merge

        images = []
        for t in tiles:
            (format, data) = self.service.renderTile(t, params.has_key('FORCE'))
            if data is None:
                continue
            images.append(data)

        if not images:
            return (format, None)
        else:
            return (format, image_merge.merge(*images))

class PILMerger(ImageMerger):
    # The default behavior of the PILMerger doesn't use the same composition
    # algorithm as Mapserver, which can change colors of merged images.
    # PIL doesn't expose a composition algorithm which does what we need, so
    # the correct implementation is pure Python which can be very slow and is
    # not enabled by default.
    USE_SLOW_BUT_CORRECT_COMPOSITING = False

    @staticmethod
    def available():
        try:
            import PIL.Image
        except ImportError:
            return False
        return True

    def _compose(self, img1, img2):
        """Alpha compositing using associative approach."""
        import PIL.Image as Image
        assert img1.size == img2.size
        assert img1.mode == "RGBA"
        assert img2.mode == "RGBA"
        img1_data = img1.getdata()
        img2_data = img2.getdata()
        result_data = []
        for p1, p2 in zip(img1_data, img2_data):
            a1 = p1[3] / 255.0
            a2 = p2[3] / 255.0
            a = a1 + a2 * (1.0 - a1)
            if a == 0:
                m = sys.maxint
            else:
                m = 1. / a
            r = [int((v1 * a1 + v2 * a2 * (1.0 - a1)) * m) for (v1, v2) in zip(p1[:3], p2[:3])]
            r.append(int(a * 255))
            r = tuple(r)
            result_data.append(r)
        img1.putdata(result_data)
        return img1

    def merge(self, tiles, params):
        import PIL.Image as Image
        result = None
        for t in tiles:
            (format, data) = self.service.renderTile(t, params.has_key('FORCE'))
            if data is None:
                continue
            image = Image.open(StringIO.StringIO(data))
            if not result:
                result = image
            else:
                if self.USE_SLOW_BUT_CORRECT_COMPOSITING:
                    result = self._compose(result, image)
                else:
                    result.paste(image, None, image)

        if result is None:
            return (format, None)
        else:
            buffer = StringIO.StringIO()
            result.save(buffer, result.format)
            buffer.seek(0)
            return (format, buffer.read())
