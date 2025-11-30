# Generate Sample Eyetracking Data
# This script creates synthetic data for demonstration purposes

# Create data directory if it doesn't exist
if (!dir.exists("data")) {
  dir.create("data")
}

set.seed(123)

# Parameters
n_subjects <- 3
n_trials <- 5
screen_width <- 1920
screen_height <- 1080
sampling_rate <- 60 # Hz
trial_duration <- 5000 # ms

# AOI definitions (for generation)
aois <- list(
  list(name = "Target", x = 960, y = 540, radius = 100),
  list(name = "Distractor", x = 400, y = 400, radius = 100)
)

# Function to generate one trial
generate_trial <- function(subject_id, trial_id) {
  n_samples <- (trial_duration / 1000) * sampling_rate
  timestamps <- seq(0, trial_duration, length.out = n_samples)
  
  # Start at center
  current_x <- screen_width / 2
  current_y <- screen_height / 2
  
  x <- numeric(n_samples)
  y <- numeric(n_samples)
  pupil <- numeric(n_samples)
  
  # Simulate fixations and saccades
  state <- "fixation"
  state_duration <- 0
  target_x <- current_x
  target_y <- current_y
  
  for (i in 1:n_samples) {
    if (state == "fixation") {
      # Add noise
      x[i] <- current_x + rnorm(1, 0, 5)
      y[i] <- current_y + rnorm(1, 0, 5)
      
      state_duration <- state_duration + (1000/sampling_rate)
      
      # Chance to switch to saccade
      if (state_duration > 300 && runif(1) < 0.05) {
        state <- "saccade"
        state_duration <- 0
        
        # Pick a target (AOI or random)
        if (runif(1) < 0.7) {
          target_aoi <- aois[[sample(length(aois), 1)]]
          target_x <- target_aoi$x + rnorm(1, 0, 20)
          target_y <- target_aoi$y + rnorm(1, 0, 20)
        } else {
          target_x <- runif(1, 0, screen_width)
          target_y <- runif(1, 0, screen_height)
        }
      }
    } else {
      # Saccade
      dx <- target_x - current_x
      dy <- target_y - current_y
      dist <- sqrt(dx^2 + dy^2)
      
      if (dist < 20) {
        state <- "fixation"
        current_x <- target_x
        current_y <- target_y
        x[i] <- current_x
        y[i] <- current_y
      } else {
        move_x <- dx * 0.2
        move_y <- dy * 0.2
        current_x <- current_x + move_x
        current_y <- current_y + move_y
        x[i] <- current_x
        y[i] <- current_y
      }
    }
    
    # Simulate pupil (baseline + random walk)
    pupil[i] <- 3000 + sin(i/50) * 100 + rnorm(1, 0, 10)
  }
  
  data.frame(
    subject_id = subject_id,
    trial_id = trial_id,
    timestamp = timestamps,
    x = x,
    y = y,
    pupil = pupil
  )
}

# Generate all data
all_data <- list()
idx <- 1

for (s in 1:n_subjects) {
  for (t in 1:n_trials) {
    trial_data <- generate_trial(s, t)
    # Add absolute timestamp
    trial_data$time <- trial_data$timestamp + (t-1) * (trial_duration + 1000)
    all_data[[idx]] <- trial_data
    idx <- idx + 1
  }
}

full_data <- do.call(rbind, all_data)

# Save raw data
write.csv(full_data, "data/raw_data.csv", row.names = FALSE)

# Create trial info
trials <- data.frame(
  trial_id = 1:n_trials,
  condition = sample(c("Control", "Experimental"), n_trials, replace = TRUE),
  stimulus = paste0("img_", 1:n_trials, ".jpg")
)
write.csv(trials, "data/trials.csv", row.names = FALSE)

# Create AOI info
aoi_df <- data.frame(
  aoi_name = c("Target", "Distractor"),
  type = "circle",
  x = c(960, 400),
  y = c(540, 400),
  width = c(100, 100), # radius
  height = c(100, 100) # radius
)
write.csv(aoi_df, "data/aois.csv", row.names = FALSE)

cat("Data generation complete.\n")
