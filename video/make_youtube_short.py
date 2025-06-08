from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx, ImageClip
import os
from typing import List, Tuple, Optional
from PIL import Image, ExifTags

# --- Function to Create YouTube Short ---
# Please, find a real example of this function in the original code.
# I've used this function as a base to create a YouTube Short from a video.
# Existing short video: https://www.youtube.com/shorts/cgypOV0XnZg

def create_youtube_short(
    input_video_path: str = "Sunset with clouds - watercolor painting n1.mp4",
    output_video_path: str = "SunsetWithClouds_short1.mp4",
    clips_of_interest: Optional[List[Tuple[float, float]]] = None,
    speed_multiplier: float = 2,
    target_aspect_ratio: Tuple[int, int] = (9, 16),
    max_duration_sec: int = 59,
    focal_points: Optional[List[Tuple[float, float]]] = None,  # <-- change here
    output_resolution: Tuple[int, int] = (1080, 1920),
    image_path: Optional[str] = None  # <-- new parameter
):
    """
    Creates a YouTube Short by extracting, speeding up, cropping, and concatenating selected segments from a video.
    Supports custom focal points for cropping and optional image fade-in/out at the end.

    Args:
        input_video_path (str): Path to the original video file.
        output_video_path (str): Path where the new Short will be saved.
        clips_of_interest (list): List of (start_time_sec, end_time_sec) tuples for segments to extract.
        speed_multiplier (int/float): Factor by which to speed up each selected clip.
        target_aspect_ratio (tuple): (width, height) tuple for the final video (e.g., (9, 16) for vertical Short).
        max_duration_sec (int): Maximum total duration for the final Short (segments are trimmed if needed).
        focal_points (list): List of (x_ratio, y_ratio) from 0.0 to 1.0, indicating crop center for each segment.
        output_resolution (tuple): Output video resolution as (width, height), e.g., (1080, 1920).
        image_path (str, optional): Path to an image to append at the end with fade-in/out transitions.
    """

    print(f"[INFO] Starting YouTube Short creation.")
    print(f"[INFO] Input video: {input_video_path}")
    print(f"[INFO] Output video: {output_video_path}")
    print(f"[INFO] Output resolution: {output_resolution}")
    print(f"[INFO] Segments to extract: {clips_of_interest}")
    print(f"[INFO] Speed multiplier: {speed_multiplier}")
    print(f"[INFO] Max duration: {max_duration_sec}s")
    print(f"[INFO] Focal points: {focal_points}")
    print(f"[INFO] Image path: {image_path}")

    try:
        original_clip = VideoFileClip(input_video_path)
        print(f"[INFO] Loaded video. Duration: {original_clip.duration:.2f}s, Size: {original_clip.size}")
    except Exception as e:
        print(f"[ERROR] Error loading video: {e}")
        return

    final_clips = []
    current_duration = 0

    for idx, (start_sec, end_sec) in enumerate(clips_of_interest):
        if current_duration >= max_duration_sec:
            print(f"[WARN] Max duration reached, skipping remaining clips.")
            break

        print(f"[INFO] Processing segment {idx+1}: {start_sec}-{end_sec}s")
        sub_clip = original_clip.subclip(start_sec, end_sec)
        sped_up_clip = sub_clip.fx(vfx.speedx, speed_multiplier)
        print(f"[DEBUG] Segment duration after speed: {sped_up_clip.duration:.2f}s")

        # Get focal point for this subclip, or default to center
        if focal_points and idx < len(focal_points):
            focal_point = focal_points[idx]
        else:
            focal_point = (0.5, 0.5)
        print(f"[DEBUG] Using focal point: {focal_point}")

        original_width, original_height = sped_up_clip.size
        target_short_width_ratio, target_short_height_ratio = target_aspect_ratio

        calculated_target_width = int(original_height * target_short_width_ratio / target_short_height_ratio)
        calculated_target_height = original_height

        if calculated_target_width > original_width:
            calculated_target_width = original_width
            calculated_target_height = int(original_width * target_short_height_ratio / target_short_width_ratio)

        focal_x_pixel = original_width * focal_point[0]
        focal_y_pixel = original_height * focal_point[1]

        x1 = int(focal_x_pixel - calculated_target_width / 2)
        y1 = int(focal_y_pixel - calculated_target_height / 2)
        x1 = max(0, x1)
        y1 = max(0, y1)
        if x1 + calculated_target_width > original_width:
            x1 = original_width - calculated_target_width
        if y1 + calculated_target_height > original_height:
            y1 = original_height - calculated_target_height
        x1 = max(0, x1)
        y1 = max(0, y1)

        print(f"[DEBUG] Cropping: x1={x1}, y1={y1}, width={calculated_target_width}, height={calculated_target_height}")

        cropped_clip = sped_up_clip.crop(
            x1=x1, y1=y1,
            width=calculated_target_width,
            height=calculated_target_height
        )

        # Resize if needed
        if cropped_clip.size != output_resolution:
            print(f"[DEBUG] Resizing from {cropped_clip.size} to {output_resolution}")
            cropped_clip = cropped_clip.resize(newsize=output_resolution)

        if current_duration + cropped_clip.duration > max_duration_sec:
            trim_duration = max_duration_sec - current_duration
            print(f"[WARN] Trimming last segment to fit max duration: {trim_duration:.2f}s")
            cropped_clip = cropped_clip.subclip(0, trim_duration)
            if cropped_clip.duration <= 0:
                print(f"[WARN] Skipping segment {idx+1}, duration after trim is zero.")
                continue

        final_clips.append(cropped_clip)
        current_duration += cropped_clip.duration
        print(f"[INFO] Added segment {idx+1}, total duration so far: {current_duration:.2f}s")

    # Add image at the end if provided
    if image_path and os.path.exists(image_path):
        print(f"[INFO] Adding multiple image fades: {image_path}")
        img = auto_orient_image(image_path)
        img.save("temp_oriented_image.jpg")
        img_w, img_h = img.size
        out_w, out_h = output_resolution

        # Scale to fit height (landscape) or width (portrait)
        if img_w > img_h:
            scale_factor = out_h / float(img_h)
            new_w = int(img_w * scale_factor)
            new_h = out_h
        else:
            scale_factor = out_w / float(img_w)
            new_w = out_w
            new_h = int(img_h * scale_factor)

        num_parts = 4
        duration_per_part = 1.5  # seconds
        fade_duration = 0.2    # seconds

        for i in range(num_parts):
            image_clip = ImageClip("temp_oriented_image.jpg").set_duration(duration_per_part)
            image_clip = image_clip.resize(newsize=(new_w, new_h))

            # Calculate crop box for each part
            if img_w > img_h:
                # Landscape: move crop window horizontally
                max_offset = new_w - out_w
                if num_parts == 1:
                    x_crop = max_offset // 2
                else:
                    x_crop = int(i * max_offset / (num_parts - 1))
                y_crop = 0
            else:
                # Portrait: move crop window vertically
                max_offset = new_h - out_h
                x_crop = 0
                if num_parts == 1:
                    y_crop = max_offset // 2
                else:
                    y_crop = int(i * max_offset / (num_parts - 1))

            # Crop to output size, no set_position needed
            image_clip = image_clip.crop(x1=x_crop, y1=y_crop, width=out_w, height=out_h)
            image_clip = image_clip.fx(vfx.fadein, fade_duration).fx(vfx.fadeout, fade_duration)
            print(f"[DEBUG] Image part {i+1}: crop=({x_crop},{y_crop}), fadein/out={fade_duration}s")
            final_clips.append(image_clip)
        print(f"[INFO] Added {num_parts} faded image parts as final clips.")

    elif image_path:
        print(f"[WARN] Image '{image_path}' not found. Skipping image addition.")

    if not final_clips:
        print("[ERROR] No clips were processed or added.")
        return

    print(f"[INFO] Concatenating {len(final_clips)} clips.")
    final_video = concatenate_videoclips(final_clips)

    # --- Adjust Aspect Ratio with Custom Focal Point ---
    original_width, original_height = final_video.size
    target_short_width_ratio, target_short_height_ratio = target_aspect_ratio[0], target_aspect_ratio[1]

    # Calculate target dimensions that fit within the original while maintaining aspect ratio
    # If original is 16:9 (wider) and target is 9:16 (taller)
    # We want to maintain the original height and calculate the target width based on 9:16
    calculated_target_width = int(original_height * target_short_width_ratio / target_short_height_ratio)
    calculated_target_height = original_height # We aim to keep the full original height if possible

    # If the calculated_target_width is wider than original (meaning original is already 9:16 or narrower)
    # then we'd need to adjust height instead.
    if calculated_target_width > original_width:
        calculated_target_width = original_width
        calculated_target_height = int(original_width * target_short_height_ratio / target_short_width_ratio)
        # This handles cases where your source might already be vertical or square

    # Calculate the crop box coordinates
    focal_x_pixel = original_width * focal_points[0][0]
    focal_y_pixel = original_height * focal_points[0][1]

    # Calculate top-left corner (x1, y1) of the crop box
    x1 = int(focal_x_pixel - calculated_target_width / 2)
    y1 = int(focal_y_pixel - calculated_target_height / 2)

    # Ensure crop box stays within original video boundaries
    x1 = max(0, x1) # Don't go left of 0
    y1 = max(0, y1) # Don't go above 0

    # Adjust x1, y1 if cropping would extend beyond the right/bottom edge
    if x1 + calculated_target_width > original_width:
        x1 = original_width - calculated_target_width
    if y1 + calculated_target_height > original_height:
        y1 = original_height - calculated_target_height

    # Ensure x1, y1 are not negative after adjustments (should already be covered by max(0, x1/y1) but good for robustness)
    x1 = max(0, x1)
    y1 = max(0, y1)


    # Perform the crop
    final_video = final_video.crop(x1=x1, y1=y1,
                                   width=calculated_target_width,
                                   height=calculated_target_height)

    # Optional: Resize to a standard Short resolution (e.g., 1080x1920) if it's not already
    # This might be needed if original_height was lower than 1920, for example.
    # We maintain aspect ratio, so only need to set one dimension.
    target_short_res_height = output_resolution[1]
    target_short_res_width = output_resolution[0]
    if final_video.h != target_short_res_height or final_video.w != target_short_res_width:
        final_video = final_video.resize(newsize=output_resolution)


    print(f"Final Short duration: {final_video.duration:.2f} seconds")
    print(f"Final Short resolution: {final_video.size[0]}x{final_video.size[1]}")

    # Write the output video
    try:
        final_video.write_videofile(
            output_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=original_clip.fps
        )
        print(f"YouTube Short successfully created at: {output_video_path}")
    except Exception as e:
        print(f"Error writing video file: {e}")
    finally:
        original_clip.close()
        for clip in final_clips:
            clip.close()
        final_video.close()

def auto_orient_image(image_path):
    img = Image.open(image_path)
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = img._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation, None)
            if orientation_value == 3:
                img = img.rotate(180, expand=True)
            elif orientation_value == 6:
                img = img.rotate(270, expand=True)
            elif orientation_value == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass
    return img

# --- Example Usage with a Custom Focal Point ---
if __name__ == "__main__":
    input_video = "Sunset with clouds - watercolor painting n1.mp4" # <--- Change this to your input video
    output_short = "SunsetWithClouds_short2.mp4" # <--- Desired output filename

    
    timelapse_clips = [
    (157, 162),  # Wetting the paper / initial brush strokes
    (192, 197),  # Applying yellow wash
    (225, 230),  # Adding orange hues
    (245, 250),  # Blending blues and purples in the sky
    (389, 394),  # Painting clouds
    (470, 475),  # Refining cloud shapes with brush
    (662, 667),  # Painting distant land and reflections
    (793, 798),  # Adjusting the horizon line
    (1082, 1087), # Repainting water reflections
    (1315, 1320), # Painting the foreground tree trunk
    (1460, 1465), # Adding details/branches to the tree
    (1686, 1691)  # Final brushstrokes for contrast and refinement
]

    # --- Custom Focal Point Examples ---
    # (0.5, 0.5) is dead center (default)
    # (0.2, 0.7) means 20% from the left, 70% from the top (closer to bottom-left)
    # (0.8, 0.3) means 80% from the left, 30% from the top (closer to top-right)
    focal_points = [
        (0.3, 0.5),
        (0.35, 0.5),
        (0.32, 0.5), 
        (0.7, 0.5),
        (0.3, 0.5),
        (0.25, 0.4), 
        (0.3, 0.5),
        (0.3, 0.5),
        (0.4, 0.5), 
        (0.5, 0.5),
        (0.55, 0.5),
        (0.4, 0.5),                     
    ]

    image_path = "IMG20250524215429.jpg"  # <-- Path to your image

    # --- Parameters ---
    max_duration_sec = 20
    image_duration = 5  # seconds
    segments_count = len(timelapse_clips)
    available_time = max_duration_sec - image_duration

    if available_time <= 0:
        raise ValueError("max_duration_sec is too short for the image duration.")

    # Calculate equal segment length (in seconds)
    segment_length = available_time / segments_count

    # Build new segments list with equal length
    equal_segments = []
    for start, _ in timelapse_clips:
        equal_segments.append((start, start + segment_length))

    if not os.path.exists(input_video):
        print(f"Error: Input video '{input_video}' not found. Please provide a valid path.")
    else:
        create_youtube_short(
            input_video_path=input_video,
            output_video_path=output_short,
            clips_of_interest=equal_segments,
            speed_multiplier=1,
            target_aspect_ratio=(9, 16),
            max_duration_sec=max_duration_sec,
            focal_points=focal_points,
            image_path=image_path
        )