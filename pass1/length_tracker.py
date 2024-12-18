class LengthTracker:
    def __init__(self):
        self.block_lengths = {
            "DEFAULT": 0,
            "DEFAULTB": 0,
            "CDATA": 0,
            "CBLKS": 0
        }
        self.current_block = "DEFAULT"
        self.max_locations = {
            "DEFAULT": 0,
            "DEFAULTB": 0,
            "CDATA": 0,
            "CBLKS": 0
        }

    def update_from_location(self, location, block):
        if location is not None:
            self.max_locations[block] = max(self.max_locations[block], location)
            self.block_lengths[block] = self.max_locations[block]

    def get_block_length(self, block):
        return self.block_lengths[block]

    def get_all_lengths(self):
        return self.block_lengths