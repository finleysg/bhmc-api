class PlayerScore:
    def __init__(self, event, player, course, score_type):
        self.event = event.id
        self.player = player.id
        self.course = course.id
        self.score_type = score_type
        self.hole1 = 0
        self.hole2 = 0
        self.hole3 = 0
        self.hole4 = 0
        self.hole5 = 0
        self.hole6 = 0
        self.hole7 = 0
        self.hole8 = 0
        self.hole9 = 0

    def total_score(self):
        return self.hole1+self.hole2+self.hole3+self.hole4+self.hole5+self.hole6+self.hole7+self.hole8+self.hole9

    def __str__(self):
        return f"{self.player} ({self.course} {self.score_type}): {self.total_score()}"


def is_hole_scores(sheet):
    if "hole" in sheet.name.lower() and "points" in sheet.name.lower():
        return True
    return False


def get_score_type(sheet_name):
    if "gross" in sheet_name.lower():
        return "gross"
    if "net" in sheet_name.lower():
        return "net"
    return "invalid"


def get_course(sheet_name):
    if "east" in sheet_name.lower():
        return "East"
    if "north" in sheet_name.lower():
        return "North"
    if "west" in sheet_name.lower():
        return "West"
    return "invalid"


def get_score_rows(sheet):
    for row_index in range(sheet.nrows):
        value = sheet.cell(row_index, 0).value
        if value != "" and \
                "gross score" not in value.lower() and \
                "net score" not in value.lower() and \
                "to par" not in value.lower() and \
                "strokes" not in value.lower() and \
                "flight" not in value.lower() and \
                "bl[" not in value.lower():
            yield row_index


def get_player_name(name, gross_or_net):
    if gross_or_net == "net":
        tokens = name.split()
        return " ".join(tokens[:-1])
    return name


def get_scores(sheet, row_index):
    try:
        return {
            1: int(sheet.cell(row_index, 1).value),
            2: int(sheet.cell(row_index, 2).value),
            3: int(sheet.cell(row_index, 3).value),
            4: int(sheet.cell(row_index, 4).value),
            5: int(sheet.cell(row_index, 5).value),
            6: int(sheet.cell(row_index, 6).value),
            7: int(sheet.cell(row_index, 7).value),
            8: int(sheet.cell(row_index, 8).value),
            9: int(sheet.cell(row_index, 9).value),
        }
    except:
        return None
