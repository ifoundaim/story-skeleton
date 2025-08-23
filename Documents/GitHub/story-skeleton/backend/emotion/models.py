EMOTION_DIMENSIONS = ["joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"]
EMOTION_DIM = len(EMOTION_DIMENSIONS)
EMOTION_MIN = -1.0
EMOTION_MAX = 1.0


def zero_emotion_vector():
    return [0.0] * EMOTION_DIM


def clip_emotion_vector(vec):
    return [max(EMOTION_MIN, min(EMOTION_MAX, float(v))) for v in vec]


class EmotionState:
    def __init__(self, player_id, vector=None, log=None):
        self.player_id = player_id
        self.vector = vector if vector is not None else zero_emotion_vector()
        self.log = log if log is not None else []

    def apply_delta(self, delta, scene_tag):
        self.vector = clip_emotion_vector([v + d for v, d in zip(self.vector, delta)])
        self.log.append({"sceneTag": scene_tag, "delta": delta})
        if len(self.log) > 50:
            self.log = self.log[-50:]

    def to_dict(self):
        return {"vector": self.vector, "log": self.log}

    @staticmethod
    def from_dict(player_id, data):
        return EmotionState(player_id, data.get("vector"), data.get("log")) 