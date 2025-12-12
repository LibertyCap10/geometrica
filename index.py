import pygame
import sys
import random
import math

# --- Settings ---
FPS = 60

# World size
WORLD_W = 3200
WORLD_H = 2400

PLAYER_BASE_SPEED = 8.0
PLAYER_RADIUS = 16

BULLET_SPEED = 10
BULLET_RADIUS = 4

# Fire rate (auto-shoot)
FIRE_RATE_START = 2.0                  # base 2 shots/second
FIRE_RATE_INCREASE_PER_POWER = 1.0     # +1.0 shots/sec per pickup

# Enemy spawn
ENEMY_SPAWN_INTERVAL_MS = 500          # faster early spawns
MIN_SPAWN_INTERVAL_MS = 200
SPAWN_ACCEL_PER_SEC = 10

EXTRA_LIFE_THRESHOLDS = [1000, 5000, 10000]
MULTIPLIER_START = 1.0

# Fire-rate score thresholds (global 2x)
FIRE_RATE_SCORE_THRESHOLDS = [50000, 150000, 300000]

# Speed boost
BOOST_DURATION_MS = 2000
BOOST_COOLDOWN_MS = 20000
BOOST_MULTIPLIER = 2.0

# Gates
GATE_LENGTH = 160
GATE_THICKNESS = 8
GATE_AOE_RADIUS = 180
GATE_MOVE_SPEED = 0.35  # slow drifting speed

# Fire-rate powerup (frequency)
FIRE_POWERUP_INTERVAL_MS = 20000
FIRE_POWERUP_RADIUS = 10
MAX_FIRE_POWERUPS = 3

# Attraction behaviour
ORB_ATTRACT_RADIUS = 220
ORB_ATTRACT_SPEED = 4.0
POWER_ATTRACT_RADIUS = 220
POWER_ATTRACT_SPEED = 4.0

# Boss spawn conditions
BOSS1_SPAWN_TIME_SEC = 60            # Boss I at 1:00
BOSS2_SPAWN_SCORE = 250_000          # Boss II at 250k
BOSS3_SPAWN_SCORE = 500_000          # Boss III at 500k
BOSS4_SPAWN_SCORE = 1_000_000        # Boss IV at 1M

# Boss stats
BOSS1_HEALTH = 50
BOSS2_HEALTH = 200
BOSS3_HEALTH = 1000
BOSS4_HEALTH = 1000                  # nerfed (was 2000)

# New boss point values (large rewards)
BOSS1_POINTS = 1000
BOSS2_POINTS = 800
BOSS3_POINTS = 600
BOSS4_POINTS = 500

BOSS_SPEED = 1.0
BOSS_SHOOT_INTERVAL_MS = 2000
BOSS4_SHOOT_INTERVAL_MS = 400        # nerfed (was 200) slower streams
BOSS_BULLET_SPEED = 6

# Star-swarm enemy
STAR_ENEMY_SCORE_THRESHOLD = 750_000
STAR_GROUP_INTERVAL_MS = 5000
STAR_ENEMY_SPEED = 7.0
STAR_ENEMY_POINTS = 20

# Bombs
BOMB_START = 2
BOMB_SCORE_THRESHOLDS = [500_000, 1_000_000]

# Enemies (+30% speed)
ENEMY_TYPES = {
    "triangle": {"color": (0, 255, 255), "speed": 3.8 * 1.3, "radius": 14, "points": 5},
    "square":   {"color": (255, 255, 0), "speed": 2.0 * 1.3, "radius": 18, "points": 2},
    "pentagon": {"color": (255, 0, 255), "speed": 2.8 * 1.3, "radius": 20, "points": 10},
}


class Player:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = PLAYER_RADIUS
        self.base_speed = PLAYER_BASE_SPEED
        self.speed = self.base_speed

        self.lives = 3
        self.invincible = False
        self.invincible_until = 0

        self.boost_active = False
        self.boost_end_time = 0
        self.last_boost_time = -BOOST_COOLDOWN_MS

        self.prev_pos = self.pos.copy()
        self.vel = pygame.math.Vector2(0, 0)

        # Rotation (radians). 0 means facing +X (to the right).
        self.angle = 0.0

    def update_angle(self, target_angle, dt_ms):
        """
        Smoothly rotate towards target_angle using shortest angular path.
        dt_ms is frame time in milliseconds.
        """
        if target_angle is None:
            return

        dt = dt_ms / 1000.0
        # Faster snap for "flip around" feel
        max_step = 14.0 * dt  # radians per second

        # Shortest angular difference in range [-pi, pi]
        diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi

        if abs(diff) <= max_step:
            self.angle = target_angle
        else:
            self.angle += max_step * (1 if diff > 0 else -1)

    def try_activate_boost(self, now):
        """Return True if a boost actually started."""
        if self.boost_active:
            return False
        if now - self.last_boost_time >= BOOST_COOLDOWN_MS:
            self.boost_active = True
            self.boost_end_time = now + BOOST_DURATION_MS
            self.last_boost_time = now
            self.speed = self.base_speed * BOOST_MULTIPLIER
            return True
        return False

    def reset_to_center(self):
        self.pos.x = WORLD_W / 2
        self.pos.y = WORLD_H / 2
        self.prev_pos = self.pos.copy()
        self.vel.xy = (0, 0)

    def update(self, keys, dt, now):
        self.prev_pos = self.pos.copy()

        move = pygame.math.Vector2(0, 0)
        # WASD + Arrows
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize() * self.speed

        self.pos += move
        self.vel = self.pos - self.prev_pos

        # Clamp
        self.pos.x = max(self.radius, min(WORLD_W - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(WORLD_H - self.radius, self.pos.y))

        if self.invincible and now >= self.invincible_until:
            self.invincible = False

        if self.boost_active and now >= self.boost_end_time:
            self.boost_active = False
            self.speed = self.base_speed

    def draw(self, surface, cam_offset):
        x, y = self.pos - cam_offset
        r = self.radius
        thick = 3

        if self.invincible:
            color = (255, 255, 255)
        elif self.boost_active:
            color = (0, 255, 100)
        else:
            color = (0, 200, 255)

        # Local geometry: ship faces +X, opening at +X ("front")
        # Back of the ship is closed: vertical line at x = -r, plus top/bottom lines.
        back_top_local = (-r, -r)
        back_bottom_local = (-r, r)
        top_front_local = (r * 0.3, -r)
        bottom_front_local = (r * 0.3, r)

        def rotate(px, py):
            ca = math.cos(self.angle)
            sa = math.sin(self.angle)
            return (px * ca - py * sa, px * sa + py * ca)

        bt = rotate(*back_top_local)
        bb = rotate(*back_bottom_local)
        tf = rotate(*top_front_local)
        bf = rotate(*bottom_front_local)

        bt = (x + bt[0], y + bt[1])
        bb = (x + bb[0], y + bb[1])
        tf = (x + tf[0], y + tf[1])
        bf = (x + bf[0], y + bf[1])

        # Closed back and side arcs, front opening between tf and bf
        pygame.draw.line(surface, color, bt, bb, thick)   # back vertical
        pygame.draw.line(surface, color, bt, tf, thick)   # top back → top mid
        pygame.draw.line(surface, color, bb, bf, thick)   # bottom back → bottom mid


class Bullet:
    def __init__(self, x, y, direction):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = BULLET_RADIUS
        self.vel = direction.normalize() * BULLET_SPEED

    def update(self, dt):
        self.pos += self.vel

    def draw(self, surf, cam_offset):
        sx, sy = self.pos - cam_offset
        pygame.draw.circle(surf, (255, 255, 255), (int(sx), int(sy)), self.radius)

    def offscreen(self):
        return (
            self.pos.x < -20 or self.pos.x > WORLD_W + 20 or
            self.pos.y < -20 or self.pos.y > WORLD_H + 20
        )


class Enemy:
    def __init__(self, t, x, y):
        self.type = t
        d = ENEMY_TYPES[t]
        self.color = d["color"]
        self.speed = d["speed"]
        self.radius = d["radius"]
        self.points = d["points"]
        self.pos = pygame.math.Vector2(x, y)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, player, dt):
        direction = player.pos - self.pos
        if direction.length_squared() > 0:
            direction = direction.normalize()

        if self.type == "pentagon":
            perp = pygame.math.Vector2(-direction.y, direction.x)
            wob = math.sin(pygame.time.get_ticks() / 250 + self.phase) * 1.5
            self.pos += direction * self.speed + perp * wob
        else:
            self.pos += direction * self.speed

    def draw(self, surf, cam_offset):
        x, y = self.pos - cam_offset
        r = self.radius

        if self.type == "triangle":
            pts = [(x, y - r), (x - r, y + r), (x + r, y + r)]
            pygame.draw.polygon(surf, self.color, pts, 2)
        elif self.type == "square":
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (x, y)
            pygame.draw.rect(surf, self.color, rect, 2)
        else:
            pts = []
            for i in range(5):
                ang = math.radians(90 + i * 72)
                pts.append((x + r * math.cos(ang), y + r * math.sin(ang)))
            pygame.draw.polygon(surf, self.color, pts, 2)


class StarEnemy:
    """Very fast star-shaped enemies that try to box the player in as a group."""

    def __init__(self, x, y, index_in_group):
        self.type = "star"
        self.color = (255, 255, 255)
        self.speed = STAR_ENEMY_SPEED
        self.radius = 16
        self.points = STAR_ENEMY_POINTS
        self.pos = pygame.math.Vector2(x, y)
        self.group_index = index_in_group  # 0..4

    def update(self, player, dt):
        # Predict future player position based on current velocity
        prediction_factor = 18  # frames ahead-ish
        predicted_pos = player.pos + player.vel * prediction_factor

        to_target = predicted_pos - self.pos
        if to_target.length_squared() == 0:
            return
        dir_norm = to_target.normalize()
        perp = pygame.math.Vector2(-dir_norm.y, dir_norm.x)

        # Spread the group laterally around the predicted line to box in
        side_scale = (self.group_index - 2) * 0.9  # -2,-1,0,1,2
        desired = dir_norm + perp * side_scale
        if desired.length_squared() > 0:
            desired = desired.normalize() * self.speed

        self.pos += desired

    def draw(self, surf, cam_offset):
        x, y = self.pos - cam_offset
        r_outer = self.radius
        r_inner = self.radius * 0.5

        pts = []
        for i in range(10):
            ang = math.radians(90 + i * 36)
            r = r_outer if i % 2 == 0 else r_inner
            pts.append((x + r * math.cos(ang), y + r * math.sin(ang)))
        pygame.draw.polygon(surf, self.color, pts, 2)


class Explosion:
    def __init__(self, x, y, radius, color):
        self.pos = pygame.math.Vector2(x, y)
        self.base = radius
        self.color = color
        self.start = pygame.time.get_ticks()
        self.duration = 400

    def done(self, now):
        return now - self.start >= self.duration

    def draw(self, surf, cam_offset, now):
        t = (now - self.start) / self.duration
        t = max(0, min(1, t))
        radius = self.base + 25 * t
        thick = max(1, int(4 * (1 - t)))

        x, y = self.pos - cam_offset
        pygame.draw.circle(surf, self.color, (int(x), int(y)), int(radius), thick)


class Orb:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = 6
        self.color = (255, 255, 0)
        self.spawn = pygame.time.get_ticks()
        self.life = 8000
        ang = random.uniform(0, 2 * math.pi)
        self.vel = pygame.math.Vector2(math.cos(ang), math.sin(ang)) * random.uniform(0.3, 0.8)

    def update(self, dt, player_pos):
        # Attraction toward player if within radius
        to_player = player_pos - self.pos
        dist = to_player.length()
        if dist <= ORB_ATTRACT_RADIUS and dist > 0:
            direction = to_player / dist
            self.vel = direction * ORB_ATTRACT_SPEED
        self.pos += self.vel

    def expired(self, now):
        return now - self.spawn >= self.life

    def draw(self, surf, cam_offset):
        x, y = self.pos - cam_offset
        pygame.draw.circle(surf, self.color, (int(x), int(y)), self.radius, 2)
        pygame.draw.circle(surf, self.color, (int(x), int(y)), self.radius // 2)


class Gate:
    def __init__(self, p1, p2):
        self.p1 = pygame.math.Vector2(p1)
        self.p2 = pygame.math.Vector2(p2)
        self.active = True
        # Give gate a small random velocity for drifting / bouncing
        angle = random.uniform(0, 2 * math.pi)
        self.vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * GATE_MOVE_SPEED

    def update(self, dt):
        if not self.active:
            return

        # Move both endpoints
        self.p1 += self.vel
        self.p2 += self.vel

        # Bounce when center gets near edges
        center = (self.p1 + self.p2) * 0.5
        bounced = False

        margin = 100
        if center.x < margin or center.x > WORLD_W - margin:
            self.vel.x *= -1
            bounced = True
        if center.y < margin or center.y > WORLD_H - margin:
            self.vel.y *= -1
            bounced = True

        if bounced:
            # Nudge slightly inward to avoid sticking
            center = (self.p1 + self.p2) * 0.5
            offset = pygame.math.Vector2(
                max(margin - center.x, 0) - max(center.x - (WORLD_W - margin), 0),
                max(margin - center.y, 0) - max(center.y - (WORLD_H - margin), 0),
            )
            self.p1 += offset
            self.p2 += offset

    def draw(self, surf, cam_offset):
        if not self.active:
            return
        p1 = self.p1 - cam_offset
        p2 = self.p2 - cam_offset
        pygame.draw.line(surf, (0, 255, 0), p1, p2, GATE_THICKNESS)

    def center(self):
        return (self.p1 + self.p2) * 0.5

    def check_trigger(self, player_pos, player_radius):
        if not self.active:
            return False

        ap = player_pos - self.p1
        ab = self.p2 - self.p1
        ab_len_sq = ab.length_squared()
        if ab_len_sq == 0:
            dist = ap.length()
        else:
            t = max(0.0, min(1.0, ap.dot(ab) / ab_len_sq))
            closest = self.p1 + ab * t
            dist = (player_pos - closest).length()

        threshold = player_radius + GATE_THICKNESS * 0.7
        if dist <= threshold:
            self.active = False
            return True
        return False


class FireRatePowerUp:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = FIRE_POWERUP_RADIUS
        self.color = (0, 180, 255)

    def update(self, dt, player_pos):
        to_player = player_pos - self.pos
        dist = to_player.length()
        if dist <= POWER_ATTRACT_RADIUS and dist > 0:
            direction = to_player / dist
            self.pos += direction * POWER_ATTRACT_SPEED

    def draw(self, surf, cam_offset):
        x, y = self.pos - cam_offset
        pygame.draw.circle(surf, (0, 0, 0), (int(x), int(y)), self.radius + 3)
        pygame.draw.circle(surf, self.color, (int(x), int(y)), self.radius)
        pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), self.radius // 2)


class FloatingText:
    def __init__(self, text, x, y, color=(255, 255, 255), duration_ms=1000, scale=1.0):
        self.text = text
        self.pos = pygame.math.Vector2(x, y)
        self.color = color
        self.start = pygame.time.get_ticks()
        self.duration = duration_ms
        self.scale = scale

    def done(self, now):
        return now - self.start >= self.duration

    def draw(self, surf, cam_offset, now, font):
        t = (now - self.start) / self.duration
        t = max(0, min(1, t))
        alpha = int(255 * (1 - t))
        offset_y = -40 * t

        x, y = self.pos - cam_offset
        y += offset_y

        base_surf = font.render(self.text, True, self.color)
        if self.scale != 1.0:
            w, h = base_surf.get_size()
            base_surf = pygame.transform.smoothscale(
                base_surf, (int(w * self.scale), int(h * self.scale))
            )

        base_surf.set_alpha(alpha)
        rect = base_surf.get_rect(center=(int(x), int(y)))

        shadow = base_surf.copy()
        shadow.fill((0, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        shadow_rect = shadow.get_rect(center=(rect.centerx + 2, rect.centery + 2))

        surf.blit(shadow, shadow_rect)
        surf.blit(base_surf, rect)


class Boss:
    def __init__(self, name, x, y, max_health, base_points, style_id, colors):
        self.name = name
        self.pos = pygame.math.Vector2(x, y)
        base_radius = 80 if style_id == 1 else (100 if style_id == 2 else (130 if style_id == 3 else 260))
        self.radius = base_radius
        self.max_health = max_health
        self.health = max_health
        self.base_points = base_points
        self.style_id = style_id
        self.colors = colors  # tuple of main colors
        self.last_shot_time = 0

        # For oscillation (style 4)
        self.spawn_time = pygame.time.get_ticks()
        self.base_pos = self.pos.copy()

    def update(self, player, now, boss_bullets):
        if self.style_id == 4:
            # Horizontal oscillation bullet-hell boss
            t = (now - self.spawn_time) / 1000.0
            amplitude = 350
            freq = 0.4
            self.pos.x = self.base_pos.x + math.sin(t * 2 * math.pi * freq) * amplitude
            self.pos.y = self.base_pos.y

            if now - self.last_shot_time >= BOSS4_SHOOT_INTERVAL_MS:
                # Fire bullets from 8 equally spaced emitters, rotating slowly
                base_angle = t * 1.5  # rotation over time
                emitters = 8
                for i in range(emitters):
                    ang = base_angle + (2 * math.pi / emitters) * i
                    dir_vec = pygame.math.Vector2(math.cos(ang), math.sin(ang))
                    boss_bullets.append(BossBullet(self.pos.x + dir_vec.x * self.radius,
                                                   self.pos.y + dir_vec.y * self.radius,
                                                   dir_vec))
                self.last_shot_time = now
        else:
            # Homing movement toward player
            direction = player.pos - self.pos
            if direction.length_squared() > 0:
                self.pos += direction.normalize() * BOSS_SPEED

            # Slow aimed shots toward player
            if now - self.last_shot_time >= BOSS_SHOOT_INTERVAL_MS:
                direction = player.pos - self.pos
                if direction.length_squared() > 0:
                    boss_bullets.append(BossBullet(self.pos.x, self.pos.y, direction))
                    self.last_shot_time = now

    def draw_mandala(self, surf, cam_offset):
        cx, cy = self.pos - cam_offset
        R = self.radius
        c1, c2, c3 = self.colors

        # Base circles
        pygame.draw.circle(surf, c1, (int(cx), int(cy)), int(R), 2)
        pygame.draw.circle(surf, c2, (int(cx), int(cy)), int(R * 0.7), 2)
        pygame.draw.circle(surf, c3, (int(cx), int(cy)), int(R * 0.4), 1)

        if self.style_id >= 1:
            # Overlapping square/star
            sq_r = R * 0.7
            pts1 = [
                (cx - sq_r, cy - sq_r),
                (cx + sq_r, cy - sq_r),
                (cx + sq_r, cy + sq_r),
                (cx - sq_r, cy + sq_r),
            ]
            pygame.draw.polygon(surf, c1, pts1, 1)

            pts2 = []
            for angle_deg in range(0, 360, 90):
                ang = math.radians(angle_deg + 45)
                pts2.append((cx + sq_r * math.cos(ang), cy + sq_r * math.sin(ang)))
            pygame.draw.polygon(surf, c3, pts2, 1)

        if self.style_id >= 2:
            # Extra ring & petals
            pygame.draw.circle(surf, c2, (int(cx), int(cy)), int(R * 0.9), 1)
            for angle_deg in range(0, 360, 30):
                ang = math.radians(angle_deg)
                x2 = cx + R * 0.9 * math.cos(ang)
                y2 = cy + R * 0.9 * math.sin(ang)
                pygame.draw.circle(surf, c3, (int(x2), int(y2)), 6, 1)

        if self.style_id >= 3:
            # Dense radial lines + inner star
            for angle_deg in range(0, 360, 15):
                ang = math.radians(angle_deg)
                x2 = cx + R * math.cos(ang)
                y2 = cy + R * math.sin(ang)
                pygame.draw.line(surf, c2, (cx, cy), (x2, y2), 1)

            inner_r = R * 0.5
            star_pts = []
            for i in range(10):
                ang = math.radians(90 + i * 36)
                r = inner_r if i % 2 == 0 else inner_r * 0.6
                star_pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            pygame.draw.polygon(surf, c1, star_pts, 1)

        if self.style_id >= 4:
            # Extra mandala layers for the final boss
            pygame.draw.circle(surf, c3, (int(cx), int(cy)), int(R * 0.2), 1)
            for angle_deg in range(0, 360, 22):
                ang = math.radians(angle_deg)
                x2 = cx + R * 0.6 * math.cos(ang)
                y2 = cy + R * 0.6 * math.sin(ang)
                pygame.draw.circle(surf, c1, (int(x2), int(y2)), 4, 0)

    def draw_healthbar(self, surf, cam_offset):
        cx, cy = self.pos - cam_offset
        bar_width = self.radius * 2
        bar_height = 10
        bar_x = cx - bar_width / 2
        bar_y = cy - self.radius - 20

        # Background
        pygame.draw.rect(
            surf, (0, 0, 0),
            pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        )
        pygame.draw.rect(
            surf, (255, 255, 255),
            pygame.Rect(bar_x, bar_y, bar_width, bar_height),
            2
        )

        ratio = max(0.0, self.health / self.max_health)
        if ratio > 0:
            pygame.draw.rect(
                surf, (0, 255, 100),
                pygame.Rect(bar_x + 2, bar_y + 2, (bar_width - 4) * ratio, bar_height - 4)
            )

    def draw(self, surf, cam_offset, font_small):
        self.draw_mandala(surf, cam_offset)
        self.draw_healthbar(surf, cam_offset)

        # Name label
        cx, cy = self.pos - cam_offset
        label = font_small.render(self.name, True, (255, 255, 255))
        rect = label.get_rect(center=(int(cx), int(cy + self.radius + 18)))
        surf.blit(label, rect)


class BossBullet:
    def __init__(self, x, y, direction):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = 6
        if direction.length_squared() == 0:
            direction = pygame.math.Vector2(0, 1)
        self.vel = direction.normalize() * BOSS_BULLET_SPEED

    def update(self, dt):
        self.pos += self.vel

    def draw(self, surf, cam_offset):
        x, y = self.pos - cam_offset
        pygame.draw.circle(surf, (255, 80, 200), (int(x), int(y)), self.radius)

    def offscreen(self):
        return (
            self.pos.x < -50 or self.pos.x > WORLD_W + 50 or
            self.pos.y < -50 or self.pos.y > WORLD_H + 50
        )


def spawn_enemy():
    corner = random.choice(["tl", "tr", "bl", "br"])
    m = 40
    if corner == "tl":
        x, y = m, m
    elif corner == "tr":
        x, y = WORLD_W - m, m
    elif corner == "bl":
        x, y = m, WORLD_H - m
    else:
        x, y = WORLD_W - m, WORLD_H - m

    t = random.choices(["triangle", "square", "pentagon"], weights=[0.4, 0.4, 0.2])[0]
    return Enemy(t, x, y)


def circle_coll(a, ar, b, br):
    return a.distance_to(b) <= (ar + br)


def spawn_single_gate():
    margin = 400
    cx = random.randint(margin, WORLD_W - margin)
    cy = random.randint(margin, WORLD_H - margin)
    center = pygame.math.Vector2(cx, cy)
    if random.random() < 0.5:
        dir_vec = pygame.math.Vector2(1, 0)
    else:
        dir_vec = pygame.math.Vector2(0, 1)
    half = (GATE_LENGTH / 2) * dir_vec
    p1 = center - half
    p2 = center + half
    return Gate(p1, p2)


def spawn_gates():
    gates = []
    for _ in range(12):
        gates.append(spawn_single_gate())
    return gates


def spawn_fire_powerup():
    margin = 200
    x = random.randint(margin, WORLD_W - margin)
    y = random.randint(margin, WORLD_H - margin)
    return FireRatePowerUp(x, y)


def spawn_star_group(player_pos):
    """Spawn 5 star enemies in a group attempting to encircle the player."""
    group = []
    base_dist = 700
    angle = random.uniform(0, 2 * math.pi)
    center = player_pos + pygame.math.Vector2(math.cos(angle), math.sin(angle)) * base_dist
    for i in range(5):
        offset_angle = angle + (i - 2) * math.radians(10)
        spawn_pos = center + pygame.math.Vector2(
            math.cos(offset_angle), math.sin(offset_angle)
        ) * 60
        group.append(StarEnemy(spawn_pos.x, spawn_pos.y, i))
    return group


def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen_w, screen_h = screen.get_size()
    pygame.display.set_caption("Geometrica")

    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("consolas", 28)
    timer_font = pygame.font.SysFont("consolas", 64, bold=True)
    small_font = pygame.font.SysFont("consolas", 22)
    tiny_font = pygame.font.SysFont("consolas", 18)
    title_font = pygame.font.SysFont("consolas", 96, bold=True)

    player = Player(WORLD_W / 2, WORLD_H / 2)

    bullets = []
    enemies = []
    explosions = []
    orbs = []
    gates = spawn_gates()
    fire_powerups = []
    floating_texts = []
    bosses = []
    boss_bullets = []

    # Boss spawn flags
    boss1_spawned = False
    boss2_spawned = False
    boss3_spawned = False
    boss4_spawned = False

    score = 0
    multiplier = MULTIPLIER_START
    fire_rate = FIRE_RATE_START
    last_shot = 0
    last_spawn = 0
    last_fire_power_spawn = -FIRE_POWERUP_INTERVAL_MS

    # Star swarm
    last_star_spawn = 0

    # Early-game triangle bursts
    last_triangle_burst = 0
    TRIANGLE_BURST_INTERVAL_MS = 5000  # every 5 seconds in early game
    EARLY_GAME_DURATION_SEC = 30

    extra_index = 0
    state = "start_menu"  # "start_menu", "playing", "paused", "respawning", "game_over"
    game_start_time = None  # set when leaving start_menu
    respawn_start_time = None
    respawn_duration_ms = 3000

    fire_rate_bonus_index = 0  # for score-based 2x milestones

    # Bombs
    bombs = BOMB_START
    bomb_bonus_index = 0
    bombs_used = 0

    # --- Stats tracking ---
    enemies_killed = 0
    enemies_killed_by_gate = 0
    boss1_killed = False
    boss2_killed = False
    boss3_killed = False
    boss4_killed = False
    orbs_collected = 0
    powerups_collected = 0
    gates_triggered = 0
    boost_uses = 0
    extra_lives_earned = 0
    fire_rate_doubles = 0
    event_log = []

    def format_time_str(sec):
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m:02d}:{s:02d}"

    def log_event(message, elapsed_seconds):
        nonlocal event_log
        ts = format_time_str(elapsed_seconds)
        event_log.append(f"{ts}  {message}")
        if len(event_log) > 40:
            event_log.pop(0)

    def clear_playfield_for_respawn(now):
        """Clear enemies/projectiles, reset player position & invincibility."""
        nonlocal bullets, enemies, explosions, orbs, fire_powerups, boss_bullets
        bullets = []
        enemies = []
        explosions = []
        orbs = []
        fire_powerups = []
        boss_bullets = []
        player.reset_to_center()
        player.invincible = True
        player.invincible_until = now + respawn_duration_ms + 1000

    def spawn_boss1(elapsed_sec):
        nonlocal bosses, boss1_spawned
        boss1_spawned = True
        colors = ((170, 120, 255), (200, 200, 255), (255, 255, 255))
        bosses.append(
            Boss("BOSS I", WORLD_W / 2, WORLD_H / 2, BOSS1_HEALTH, BOSS1_POINTS, 1, colors)
        )
        log_event("Boss I appeared", elapsed_sec)

    def spawn_boss2(elapsed_sec):
        nonlocal bosses, boss2_spawned
        boss2_spawned = True
        colors = ((255, 255, 255), (200, 200, 220), (255, 105, 180))  # white/silver/pink
        bosses.append(
            Boss("BOSS II", WORLD_W / 2 + 300, WORLD_H / 2 - 200,
                 BOSS2_HEALTH, BOSS2_POINTS, 2, colors)
        )
        log_event("Boss II appeared", elapsed_sec)

    def spawn_boss3(elapsed_sec):
        nonlocal bosses, boss3_spawned
        boss3_spawned = True
        colors = ((255, 215, 0), (200, 30, 30), (0, 0, 0))  # gold/red/black
        bosses.append(
            Boss("BOSS III", WORLD_W / 2 - 350, WORLD_H / 2 + 250,
                 BOSS3_HEALTH, BOSS3_POINTS, 3, colors)
        )
        log_event("Boss III appeared", elapsed_sec)

    def spawn_boss4(elapsed_sec):
        nonlocal bosses, boss4_spawned
        boss4_spawned = True
        colors = ((255, 215, 0), (255, 50, 50), (0, 0, 0))  # intense gold/red/black
        bosses.append(
            Boss("BOSS IV", WORLD_W / 2, WORLD_H / 2 - 150,
                 BOSS4_HEALTH, BOSS4_POINTS, 4, colors)
        )
        log_event("Boss IV appeared", elapsed_sec)

    def use_bomb(elapsed_sec):
        nonlocal enemies, bullets, boss_bullets, bombs, bombs_used, orbs
        if bombs <= 0:
            return
        bombs -= 1
        bombs_used += 1

        # Make all non-boss enemies drop orbs and explode, even when cleared by bomb
        for en in enemies:
            explosions.append(Explosion(en.pos.x, en.pos.y, en.radius, en.color))
            orbs.append(Orb(en.pos.x, en.pos.y))

        enemies = []       # enemies cleared
        bullets = []       # clear player bullets
        boss_bullets = []  # clear boss bullets, but bosses remain

        explosions.append(
            Explosion(player.pos.x, player.pos.y, 300, (255, 255, 255))
        )
        floating_texts.append(
            FloatingText("BOMB!", player.pos.x, player.pos.y - 40,
                         (255, 80, 80), duration_ms=1200, scale=1.8)
        )
        log_event("Bomb detonated", elapsed_sec)

    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()

        if game_start_time is None:
            elapsed_ms = 0
        else:
            elapsed_ms = now - game_start_time
        elapsed_sec = elapsed_ms / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if state == "playing":
                        state = "paused"
                    elif state == "paused":
                        state = "playing"
                    elif state == "respawning":
                        # ignore ESC during respawn
                        pass
                    elif state == "game_over":
                        running = False
                    elif state == "start_menu":
                        running = False
                # Start menu: select START
                elif state == "start_menu" and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    state = "playing"
                    if game_start_time is None:
                        game_start_time = pygame.time.get_ticks()
                elif e.key == pygame.K_SPACE and state == "playing":
                    if player.try_activate_boost(now):
                        boost_uses += 1
                        log_event("Boost activated", elapsed_sec)
                elif e.key == pygame.K_e and state == "playing":
                    use_bomb(elapsed_sec)

                if state == "paused" and e.key == pygame.K_q:
                    running = False

                if state == "game_over" and e.key == pygame.K_r:
                    return main()

        keys = pygame.key.get_pressed()

        # --- STATE: PLAYING ---
        if state == "playing":
            player.update(keys, dt, now)

            # Move gates (bouncy)
            for gate in gates:
                gate.update(dt)

            # Spawn scaling
            current_spawn_interval = max(
                MIN_SPAWN_INTERVAL_MS,
                ENEMY_SPAWN_INTERVAL_MS - elapsed_sec * SPAWN_ACCEL_PER_SEC,
            )
            if now - last_spawn >= current_spawn_interval:
                # Early game: bias toward triangles to keep player moving
                if elapsed_sec < EARLY_GAME_DURATION_SEC and random.random() < 0.6:
                    # Triangle-only spawn from a corner
                    corner = random.choice(["tl", "tr", "bl", "br"])
                    m = 40
                    if corner == "tl":
                        x, y = m, m
                    elif corner == "tr":
                        x, y = WORLD_W - m, m
                    elif corner == "bl":
                        x, y = m, WORLD_H - m
                    else:
                        x, y = WORLD_W - m, WORLD_H - m
                    enemies.append(Enemy("triangle", x, y))
                else:
                    enemies.append(spawn_enemy())
                last_spawn = now

            # Early-game triangle bursts
            if elapsed_sec < EARLY_GAME_DURATION_SEC and now - last_triangle_burst >= TRIANGLE_BURST_INTERVAL_MS:
                for _ in range(7):
                    corner = random.choice(["tl", "tr", "bl", "br"])
                    m = 40
                    jitter = 80
                    if corner == "tl":
                        x = m + random.randint(0, jitter)
                        y = m + random.randint(0, jitter)
                    elif corner == "tr":
                        x = WORLD_W - m - random.randint(0, jitter)
                        y = m + random.randint(0, jitter)
                    elif corner == "bl":
                        x = m + random.randint(0, jitter)
                        y = WORLD_H - m - random.randint(0, jitter)
                    else:
                        x = WORLD_W - m - random.randint(0, jitter)
                        y = WORLD_H - m - random.randint(0, jitter)
                    enemies.append(Enemy("triangle", x, y))
                last_triangle_burst = now
                log_event("Triangle burst wave", elapsed_sec)

            # Fire-rate powerups
            if (now - last_fire_power_spawn >= FIRE_POWERUP_INTERVAL_MS and
                    len(fire_powerups) < MAX_FIRE_POWERUPS):
                fire_powerups.append(spawn_fire_powerup())
                last_fire_power_spawn = now

            # Boss spawns
            if (not boss1_spawned) and elapsed_sec >= BOSS1_SPAWN_TIME_SEC:
                spawn_boss1(elapsed_sec)

            if (not boss2_spawned) and score >= BOSS2_SPAWN_SCORE:
                spawn_boss2(elapsed_sec)

            if (not boss3_spawned) and score >= BOSS3_SPAWN_SCORE:
                spawn_boss3(elapsed_sec)

            if (not boss4_spawned) and score >= BOSS4_SPAWN_SCORE:
                spawn_boss4(elapsed_sec)

            # Star swarm spawns (late-game)
            if score >= STAR_ENEMY_SCORE_THRESHOLD and now - last_star_spawn >= STAR_GROUP_INTERVAL_MS:
                enemies.extend(spawn_star_group(player.pos))
                last_star_spawn = now
                log_event("Star swarm appeared", elapsed_sec)

            # Auto-shoot: rotate ship toward target, fire from actual nose
            cooldown_ms = 1000.0 / fire_rate
            target_pos = None

            if bosses:
                nearest_boss = min(bosses, key=lambda b: b.pos.distance_to(player.pos))
                target_pos = nearest_boss.pos
            elif enemies:
                nearest = min(enemies, key=lambda e: e.pos.distance_to(player.pos))
                target_pos = nearest.pos

            desired_angle = None
            if target_pos is not None:
                to_target = target_pos - player.pos
                if to_target.length_squared() > 0:
                    desired_angle = math.atan2(to_target.y, to_target.x)

            # Smoothly rotate toward desired angle (snappier)
            player.update_angle(desired_angle, dt)

            # Fire in facing direction from front opening
            if target_pos is not None and now - last_shot >= cooldown_ms:
                forward = pygame.math.Vector2(math.cos(player.angle), math.sin(player.angle))
                if forward.length_squared() > 0:
                    # spawn at nose tip (front of U)
                    spawn_pos = player.pos + forward.normalize() * player.radius
                    bullets.append(Bullet(spawn_pos.x, spawn_pos.y, forward))
                    last_shot = now

            for b in bullets:
                b.update(dt)
            bullets = [b for b in bullets if not b.offscreen()]

            for en in enemies:
                en.update(player, dt)

            for boss in bosses:
                boss.update(player, now, boss_bullets)

            for bb in boss_bullets:
                bb.update(dt)
            boss_bullets = [bb for bb in boss_bullets if not bb.offscreen()]

            explosions = [ex for ex in explosions if not ex.done(now)]

            for o in orbs:
                o.update(dt, player.pos)
            orbs = [o for o in orbs if not o.expired(now)]

            for pwr in fire_powerups:
                pwr.update(dt, player.pos)

            floating_texts = [ft for ft in floating_texts if not ft.done(now)]

            # Gates + AoE
            for gate in gates:
                if gate.check_trigger(player.pos, player.radius):
                    gates_triggered += 1
                    log_event("Gate triggered", elapsed_sec)

                    center = gate.center()
                    explosions.append(Explosion(center.x, center.y, GATE_AOE_RADIUS, (0, 255, 0)))

                    for en in enemies[:]:
                        if en.pos.distance_to(center) <= GATE_AOE_RADIUS:
                            explosions.append(Explosion(en.pos.x, en.pos.y, en.radius, en.color))
                            orbs.append(Orb(en.pos.x, en.pos.y))
                            gained = int(en.points * multiplier)
                            score += gained
                            enemies_killed += 1
                            enemies_killed_by_gate += 1
                            floating_texts.append(
                                FloatingText(
                                    str(gained), en.pos.x, en.pos.y,
                                    (255, 215, 0), duration_ms=1000, scale=1.4
                                )
                            )
                            enemies.remove(en)

                    gates.append(spawn_single_gate())

            # Bullet-enemy collisions
            for b in bullets[:]:
                hit = False
                for en in enemies[:]:
                    if circle_coll(b.pos, b.radius, en.pos, en.radius):
                        explosions.append(Explosion(en.pos.x, en.pos.y, en.radius, en.color))
                        orbs.append(Orb(en.pos.x, en.pos.y))
                        gained = int(en.points * multiplier)
                        score += gained
                        enemies_killed += 1
                        floating_texts.append(
                            FloatingText(
                                str(gained), en.pos.x, en.pos.y,
                                (255, 215, 0), duration_ms=1000, scale=1.4
                            )
                        )
                        bullets.remove(b)
                        enemies.remove(en)
                        hit = True
                        break
                if hit:
                    continue

            # Bullet-boss collisions
            for b in bullets[:]:
                hit_boss = False
                for boss in bosses[:]:
                    if circle_coll(b.pos, b.radius, boss.pos, boss.radius):
                        boss.health -= 1
                        bullets.remove(b)
                        hit_boss = True
                        if boss.health <= 0:
                            explosions.append(
                                Explosion(boss.pos.x, boss.pos.y, boss.radius, boss.colors[0])
                            )

                            # Boss death: lots of orbs + large points
                            if boss.name == "BOSS I":
                                orb_count = 15
                            elif boss.name == "BOSS II":
                                orb_count = 25
                            elif boss.name == "BOSS III":
                                orb_count = 40
                            else:  # BOSS IV
                                orb_count = 70

                            for i in range(orb_count):
                                ang = (2 * math.pi * i) / orb_count
                                dist = boss.radius * random.uniform(0.3, 0.9)
                                pos = boss.pos + pygame.math.Vector2(
                                    math.cos(ang), math.sin(ang)
                                ) * dist
                                orbs.append(Orb(pos.x, pos.y))

                            gained = int(boss.base_points * multiplier)
                            score += gained
                            floating_texts.append(
                                FloatingText(
                                    str(gained), boss.pos.x, boss.pos.y,
                                    (255, 200, 255), duration_ms=1200, scale=1.6
                                )
                            )
                            if boss.name == "BOSS I":
                                boss1_killed = True
                                log_event("Boss I defeated", elapsed_sec)
                            elif boss.name == "BOSS II":
                                boss2_killed = True
                                log_event("Boss II defeated", elapsed_sec)
                            elif boss.name == "BOSS III":
                                boss3_killed = True
                                log_event("Boss III defeated", elapsed_sec)
                            elif boss.name == "BOSS IV":
                                boss4_killed = True
                                log_event("Boss IV defeated", elapsed_sec)

                            bosses.remove(boss)
                        break
                if hit_boss:
                    continue

            # Player-enemy collisions
            if not player.invincible:
                for en in enemies[:]:
                    if circle_coll(player.pos, player.radius, en.pos, en.radius):
                        player.lives -= 1
                        enemies.remove(en)
                        if player.lives <= 0:
                            state = "game_over"
                        else:
                            state = "respawning"
                            respawn_start_time = now
                            clear_playfield_for_respawn(now)
                        break

            # Player-boss collisions
            if state == "playing" and not player.invincible:
                for boss in bosses:
                    if circle_coll(player.pos, player.radius, boss.pos, boss.radius):
                        player.lives -= 1
                        if player.lives <= 0:
                            state = "game_over"
                        else:
                            state = "respawning"
                            respawn_start_time = now
                            clear_playfield_for_respawn(now)
                        break

            # Player-boss-bullet collisions
            if state == "playing" and not player.invincible:
                for bb in boss_bullets[:]:
                    if circle_coll(player.pos, player.radius, bb.pos, bb.radius):
                        player.lives -= 1
                        boss_bullets.remove(bb)
                        if player.lives <= 0:
                            state = "game_over"
                        else:
                            state = "respawning"
                            respawn_start_time = now
                            clear_playfield_for_respawn(now)
                        break

            # Orb pickup
            for o in orbs[:]:
                if circle_coll(player.pos, player.radius, o.pos, o.radius):
                    multiplier += 1.0
                    orbs_collected += 1
                    orbs.remove(o)

            # Fire-rate powerup pickup
            for pwr in fire_powerups[:]:
                if circle_coll(player.pos, player.radius, pwr.pos, FIRE_POWERUP_RADIUS):
                    fire_rate += FIRE_RATE_INCREASE_PER_POWER
                    powerups_collected += 1
                    fire_powerups.remove(pwr)
                    text = f"+{FIRE_RATE_INCREASE_PER_POWER:.2f}/s"
                    floating_texts.append(
                        FloatingText(
                            text, pwr.pos.x, pwr.pos.y,
                            (0, 200, 255), duration_ms=1000, scale=1.2
                        )
                    )
                    log_event(
                        f"Fire rate increased to {fire_rate:.2f}/s", elapsed_sec
                    )

            # Extra lives
            if extra_index < len(EXTRA_LIFE_THRESHOLDS):
                if score >= EXTRA_LIFE_THRESHOLDS[extra_index]:
                    player.lives += 1
                    extra_lives_earned += 1
                    log_event(
                        f"Extra life earned (score {score})", elapsed_sec
                    )
                    extra_index += 1

            # Fire-rate score milestones (2x)
            while fire_rate_bonus_index < len(FIRE_RATE_SCORE_THRESHOLDS) and \
                    score >= FIRE_RATE_SCORE_THRESHOLDS[fire_rate_bonus_index]:
                fire_rate *= 2.0
                fire_rate_doubles += 1
                log_event("Fire rate x2 milestone reached", elapsed_sec)
                fire_rate_bonus_index += 1
                floating_texts.append(
                    FloatingText(
                        "FIRE RATE x2!", player.pos.x, player.pos.y - 40,
                        (255, 100, 0), duration_ms=1200, scale=1.6
                    )
                )

            # Bomb score milestones (+1 bomb)
            while bomb_bonus_index < len(BOMB_SCORE_THRESHOLDS) and \
                    score >= BOMB_SCORE_THRESHOLDS[bomb_bonus_index]:
                bombs += 1
                bomb_bonus_index += 1
                floating_texts.append(
                    FloatingText(
                        "+BOMB", player.pos.x, player.pos.y - 60,
                        (255, 255, 0), duration_ms=1200, scale=1.6
                    )
                )
                log_event("Bomb +1 earned", elapsed_sec)

        # --- STATE: RESPAWNING (countdown, no updates/spawns) ---
        elif state == "respawning":
            if respawn_start_time is not None:
                elapsed_respawn = now - respawn_start_time
                if elapsed_respawn >= respawn_duration_ms:
                    state = "playing"

        # --- START MENU RENDER & LOOP SHORT-CIRCUIT ---
        if state == "start_menu":
            screen.fill((0, 0, 0))

            # Title
            title_surf = title_font.render("GEOMETRICA", True, (0, 200, 255))
            title_rect = title_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 80))
            screen.blit(title_surf, title_rect)

            # Subtle glow rectangle behind title
            glow_pad_x, glow_pad_y = 40, 30
            glow_rect = pygame.Rect(
                title_rect.left - glow_pad_x // 2,
                title_rect.top - glow_pad_y // 2,
                title_rect.width + glow_pad_x,
                title_rect.height + glow_pad_y,
            )
            glow_surf = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            glow_surf.fill((10, 10, 30, 220))
            pygame.draw.rect(glow_surf, (0, 200, 255), glow_surf.get_rect(), 4)
            screen.blit(glow_surf, glow_rect.topleft)
            screen.blit(title_surf, title_rect)  # redraw on top

            # "Start" label (select with ENTER / SPACE)
            start_text = hud_font.render("START", True, (255, 255, 255))
            start_rect = start_text.get_rect(center=(screen_w // 2, screen_h // 2 + 40))
            screen.blit(start_text, start_rect)

            # Hint text
            hint_text = tiny_font.render("Press ENTER or SPACE to begin", True, (200, 200, 200))
            hint_rect = hint_text.get_rect(center=(screen_w // 2, screen_h // 2 + 90))
            screen.blit(hint_text, hint_rect)

            pygame.display.flip()
            continue  # Skip rest of drawing/logic this frame

        # Camera
        cam_x = player.pos.x - screen_w / 2
        cam_y = player.pos.y - screen_h / 2
        cam_x = max(0, min(WORLD_W - screen_w, cam_x))
        cam_y = max(0, min(WORLD_H - screen_h, cam_y))
        cam_offset = pygame.math.Vector2(cam_x, cam_y)

        # Draw background grid
        screen.fill((0, 0, 0))
        grid_color = (20, 20, 20)
        step = 40
        start_x = int(cam_x // step * step)
        end_x = int((cam_x + screen_w) // step * step + step)
        for x in range(start_x, end_x + 1, step):
            sx = x - cam_x
            pygame.draw.line(screen, grid_color, (sx, 0), (sx, screen_h))
        start_y = int(cam_y // step * step)
        end_y = int((cam_y + screen_h) // step * step + step)
        for y in range(start_y, end_y + 1, step):
            sy = y - cam_y
            pygame.draw.line(screen, grid_color, (0, sy), (screen_w, sy))

        # Draw entities
        for gate in gates:
            gate.draw(screen, cam_offset)
        for pwr in fire_powerups:
            pwr.draw(screen, cam_offset)
        for b in bullets:
            b.draw(screen, cam_offset)
        for en in enemies:
            en.draw(screen, cam_offset)
        for boss in bosses:
            boss.draw(screen, cam_offset, tiny_font)
        for bb in boss_bullets:
            bb.draw(screen, cam_offset)
        for o in orbs:
            o.draw(screen, cam_offset)
        for ex in explosions:
            ex.draw(screen, cam_offset, now)
        for ft in floating_texts:
            ft.draw(screen, cam_offset, now, hud_font)
        player.draw(screen, cam_offset)

        # --- HUD: big scoreboard timer ---
        minutes = int(elapsed_sec // 60)
        seconds = int(elapsed_sec % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        time_surf = timer_font.render(time_str, True, (255, 255, 255))
        pad_x, pad_y = 30, 20
        bg_w = time_surf.get_width() + pad_x
        bg_h = time_surf.get_height() + pad_y
        timer_bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        timer_bg.fill((0, 0, 0, 220))
        pygame.draw.rect(timer_bg, (255, 215, 0), timer_bg.get_rect(), 4)

        timer_x = (screen_w - bg_w) // 2
        timer_y = 10
        screen.blit(timer_bg, (timer_x, timer_y))
        screen.blit(time_surf, (timer_x + pad_x // 2, timer_y + pad_y // 2))

        # Other HUD
        score_text = hud_font.render(f"Score: {score}", True, (255, 255, 255))
        mult_text = hud_font.render(f"Mult: {multiplier:.1f}x", True, (255, 255, 0))
        fire_text = hud_font.render(f"Fire: {fire_rate:.2f}/s", True, (0, 200, 255))
        lives_text = hud_font.render(f"Lives: {player.lives}", True, (255, 255, 255))
        bombs_text = hud_font.render(f"Bombs: {bombs} (E)", True, (255, 100, 100))

        time_since_boost = now - player.last_boost_time
        if time_since_boost >= BOOST_COOLDOWN_MS:
            boost_str = "Boost: READY (SPACE)"
            boost_color = (0, 255, 0)
        else:
            remaining = max(0, (BOOST_COOLDOWN_MS - time_since_boost) // 1000)
            boost_str = f"Boost: {remaining}s"
            boost_color = (255, 255, 0)
        boost_text = hud_font.render(boost_str, True, boost_color)

        screen.blit(score_text, (10, 60))
        screen.blit(mult_text, (10, 95))
        screen.blit(fire_text, (10, 130))
        screen.blit(boost_text, (10, 165))
        screen.blit(bombs_text, (10, 200))
        screen.blit(lives_text, (screen_w - lives_text.get_width() - 10, 10))

        # Respawn countdown overlay
        if state == "respawning" and respawn_start_time is not None:
            overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))

            elapsed_respawn = now - respawn_start_time
            remaining = max(0, respawn_duration_ms - elapsed_respawn)
            countdown_number = int(remaining / 1000) + 1
            if countdown_number < 1:
                countdown_number = 1
            cd_surf = timer_font.render(str(countdown_number), True, (255, 255, 255))
            cd_rect = cd_surf.get_rect(center=(screen_w // 2, screen_h // 2))
            screen.blit(cd_surf, cd_rect)

        # Pause & stats / catalogue screen
        if state == "paused":
            overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))

            title = hud_font.render("PAUSED - ESC: Resume | Q: Quit", True, (255, 255, 255))
            screen.blit(
                title,
                ((screen_w - title.get_width()) // 2, screen_h // 2 - 260),
            )

            def fmt_time(sec):
                m = int(sec // 60)
                s = int(sec % 60)
                return f"{m:02d}:{s:02d}"

            # Stats block (left)
            stats_lines = [
                f"Time: {fmt_time(elapsed_sec)}",
                f"Score: {score}",
                f"Multiplier: {multiplier:.1f}x",
                f"Fire Rate: {fire_rate:.2f}/s",
                f"Lives: {player.lives}  (+{extra_lives_earned} extra)",
                f"Bombs: {bombs}  (Used: {bombs_used})",
                f"Enemies Killed: {enemies_killed}",
                f"  via Gates: {enemies_killed_by_gate}",
                f"Orbs Collected: {orbs_collected}",
                f"Fire Powerups: {powerups_collected}",
                f"Gates Triggered: {gates_triggered}",
                f"Boost Uses: {boost_uses}",
                f"Boss I Defeated: {'Yes' if boss1_killed else 'No'}",
                f"Boss II Defeated: {'Yes' if boss2_killed else 'No'}",
                f"Boss III Defeated: {'Yes' if boss3_killed else 'No'}",
                f"Boss IV Defeated: {'Yes' if boss4_killed else 'No'}",
                f"Fire Rate x2 Milestones: {fire_rate_doubles}",
            ]

            left_x = 60
            y = screen_h // 2 - 210
            for line in stats_lines:
                txt = small_font.render(line, True, (255, 255, 255))
                screen.blit(txt, (left_x, y))
                y += txt.get_height() + 3

            # Enemy & Boss Catalogue (center)
            cat_x = screen_w // 2 - 170
            y = screen_h // 2 - 210
            cat_title = small_font.render("ENEMY & BOSS CATALOGUE", True, (255, 215, 0))
            screen.blit(cat_title, (cat_x, y))
            y += cat_title.get_height() + 6

            catalogue_lines = [
                "Triangle: Fast teal chaser.",
                "  Points: 5  |  Speed: Fast",
                "Square: Slow yellow tank.",
                "  Points: 2  |  Speed: Slow",
                "Pentagon: Magenta wobbling hunter.",
                "  Points: 10 |  Speed: Medium",
                "Star Swarm: White boxing stars (5-pack).",
                "  Points: 20 |  Very fast, predictive",
                "",
                "BOSS I: Violet mandala guardian.",
                f"  HP: {BOSS1_HEALTH}  |  Base Points: {BOSS1_POINTS}",
                "  Spawns at 01:00.",
                "",
                "BOSS II: White/silver/pink mandala.",
                f"  HP: {BOSS2_HEALTH} |  Base Points: {BOSS2_POINTS}",
                "  Spawns at 250,000 score.",
                "",
                "BOSS III: Gold/red/black mandala.",
                f"  HP: {BOSS3_HEALTH} |  Base Points: {BOSS3_POINTS}",
                "  Spawns at 500,000 score.",
                "",
                "BOSS IV: Grand golden bullet mandala.",
                f"  HP: {BOSS4_HEALTH} |  Base Points: {BOSS4_POINTS}",
                "  Spawns at 1,000,000 score.",
            ]

            for line in catalogue_lines:
                txt = tiny_font.render(line, True, (220, 220, 220))
                screen.blit(txt, (cat_x, y))
                y += txt.get_height() + 2

            # Event log (right)
            log_x = screen_w - 380
            y = screen_h // 2 - 210
            header = small_font.render("Recent Events:", True, (255, 215, 0))
            screen.blit(header, (log_x, y))
            y += header.get_height() + 4

            for entry in event_log[-14:]:
                txt = tiny_font.render(entry, True, (220, 220, 220))
                screen.blit(txt, (log_x, y))
                y += txt.get_height() + 2

        elif state == "game_over":
            overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            go = hud_font.render("GAME OVER", True, (255, 80, 80))
            info = hud_font.render("Press R to Restart or ESC to Quit", True, (255, 255, 255))
            screen.blit(go, ((screen_w - go.get_width()) // 2, screen_h // 2 - 30))
            screen.blit(info, ((screen_w - info.get_width()) // 2, screen_h // 2 + 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
