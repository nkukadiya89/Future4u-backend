def format_time_diff(time_diff):
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{days} days {hours} Hrs {minutes} min {seconds} sec"
