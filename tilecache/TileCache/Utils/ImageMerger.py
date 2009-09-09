import os
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

__all__ = ['ImageMergeMerger', 'PILMerger']

class ImageMerger:
    def __init__ (self, service):
        self.service = service

    def preferred(self, tiles, params):
        """Override this method and return False is this module may not be
           the best option for the given parameters"""
        return True

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

    def preferred(self, tiles, params):
        # Empirical measurements have determined than PIL is faster when merging
        # a small number of layers. So this module shouldn't be the preferred
        # one in that case.
        # This number has been calculed by on a 64-bit Debian system.
        # Note that results are different when running on a 32-bit system.
        IMAGE_MERGE_TILES_THRESHOLD = 5

        return len(tiles) > IMAGE_MERGE_TILES_THRESHOLD

    def merge(self, tiles, params):
        import image_merge

        images = []
        for t in tiles:
            (format, data) = self.service.renderTile(t, params.has_key('FORCE'))
            if data is None:
                continue
            images.append(data)

        return (format, image_merge.merge(*images))

class PILMerger(ImageMerger):
    @staticmethod
    def available():
        try:
            import PIL.Image
        except ImportError:
            return False
        return True

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
                result.paste(image, None, image)

        if result is None:
            return (format, None)
        else:
            buffer = StringIO.StringIO()
            result.save(buffer, result.format)
            buffer.seek(0)
            return (format, buffer.read())
