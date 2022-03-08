use std::{error::Error, fs::OpenOptions};
use crate::twitter::Tweet;

pub fn write_tweet(tweet: &Tweet, file_path: &String) -> Result<(), Box<dyn Error>> {
    // let mut wtr = csv::Writer::from_writer(io::stdout());
    // wtr.serialize(tweet)?; // when writing records with Serde using structs, the header row is written automatically
    // wtr.flush()?;
    // Ok(())

    let file = OpenOptions::new()
                    .write(true)
                    .create(true)
                    .append(true)
                    .open(file_path)
                    .unwrap();
    let mut wtr = csv::Writer::from_writer(file);
    wtr.write_record(tweet.into_array())?;
    wtr.flush()?;
    Ok(())
}
