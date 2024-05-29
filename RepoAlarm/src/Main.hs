{-# LANGUAGE OverloadedStrings, QuasiQuotes, TemplateHaskell,
    TypeFamilies, LambdaCase, EmptyDataDecls, ScopedTypeVariables #-}
{-# OPTIONS -Wno-unused-top-binds #-}

module Main (main) where

import Control.Monad (forM_, when, unless)
import Data.Aeson
import Data.Aeson.Types (Parser)
import Data.Char (ord)
import Data.Functor ((<&>))
import System.Process (callProcess)
import System.Random (randomRIO)
import Yesod

import qualified Data.ByteString as BS
import qualified Data.Text as T
import qualified Network.HTTP.Simple as CL

-- webhook data types
data PipelineEvent = PipelineEvent {
    pipelineUser :: T.Text,
    pipelineStatus :: T.Text, -- could be an enum...
    pipelineCommitMessage :: T.Text
} deriving (Show, Eq, Ord)

data PushEvent = PushEvent {
    pushEventCommits :: [CommitInfo]
} deriving (Show, Eq, Ord)

data CommitInfo = CommitInfo {
    -- again, most fields ommited, as I don't need them
    commitId :: T.Text,
    commitTitle :: T.Text,
    commitAuthorName :: T.Text
} deriving (Show, Read, Eq, Ord)

instance FromJSON PipelineEvent where
    parseJSON = withObject "PipelineEvent" $ \o -> do
        objectKind <- o .: "object_kind" :: Parser T.Text
        unless (objectKind == "pipeline") $ fail $ "Not a pipeline event: " <> show objectKind

        commit <- o .: "commit"

        PipelineEvent
            <$> (commit .: "author" >>= (.: "name"))
            <*> (o .: "object_attributes" >>= (.: "status"))
            <*> commit .: "title"

instance FromJSON PushEvent where
    parseJSON = withObject "CommitInfo" $ \o -> do
        objectKind <- o .: "object_kind" :: Parser T.Text
        unless (objectKind == "push") $ fail $ "Not a push event: " <> show objectKind

        PushEvent <$> o .: "commits"

instance FromJSON CommitInfo where
    parseJSON = withObject "CommitInfo" $ \o -> do
        CommitInfo
            <$> o .: "id"
            <*> o .: "title"
            <*> (o .: "author" >>= (.: "name"))

-- gitlab API data types
data CommitInfoLong = CommitInfoLong {
    -- most fields ommited, as I don't need them
    commitDeletions :: Int,
    commitInsertions :: Int
} deriving (Show, Read, Eq, Ord)

instance FromJSON CommitInfoLong where
    parseJSON = withObject "CommitInfoLong" $ \o -> do
        stats <- o .: "stats"
        CommitInfoLong
            <$> stats .: "deletions"
            <*> stats .: "additions"


data TTSReq = TTSReq T.Text deriving (Show, Read, Eq, Ord)
instance ToJSON TTSReq where
    toJSON (TTSReq t) = object [
            "model" .= ("tts-1" :: T.Text),
            "voice" .= ("shimmer" :: T.Text),
            "input" .= t,
            "response_format" .= ("opus" :: T.Text)
            -- could change speed, but it doesn't affect cost, so I'm leaving it
            -- as default
        ]

-- data available in all handlers: text to speed API & gitlab commit API
data RepoAlarm = RepoAlarm {
    repoAlarmTTS :: TTSReq -> IO BS.ByteString,
    repoAlarmGetCommit :: String -> IO CommitInfoLong
}

-- define routes
mkYesod "RepoAlarm" [parseRoutes|
/pipeline.json PipelineR POST
/push.json     PushR     POST
|]

instance Yesod RepoAlarm where
    makeSessionBackend _ = return Nothing
    approot = ApprootStatic ""

postPipelineR :: Handler ()
postPipelineR = do
    r <- requireCheckJsonBody :: Handler PipelineEvent
    tts <- getsYesod repoAlarmTTS

    case pipelineStatus r of
        "pending" -> pure ()
        "running" -> pure ()
        "canceled" -> pure ()
        "success" -> liftIO $ callProcess "mpv" ["--", "pipeline-success.opus"]
        "failed" -> liftIO $ do
            callProcess "mpv" ["--", "pipeline-error.opus"]

            i <- randomRIO (0, 10^(9 :: Int)) :: IO Integer
            let filename = show i <> ".opus"

            opus_data <- tts $ TTSReq
                $ "Pipeline fail, wegen " <> pipelineUser r <> " bei commit " <> pipelineCommitMessage r
            BS.writeFile filename opus_data

            callProcess "mpv" ["--volume=130", "--", filename]

        _ -> $(logWarn) $ "[WARN] pipeline entered unknown state: " <> T.pack (show r)

postPushR :: Handler ()
postPushR = do
    r <- requireCheckJsonBody :: Handler PushEvent
    getCommit <- getsYesod repoAlarmGetCommit

    -- check all pushed commits
    liftIO $ forM_ (pushEventCommits r) $ \comShort -> do
        comLong <- getCommit $ T.unpack $ commitId comShort
        let dels = fromIntegral $ commitDeletions  comLong :: Double
        let ins  = fromIntegral $ commitInsertions comLong :: Double

        when (dels > 10 && dels > ins * 1.3) $ do
            print comShort
            print comLong
            callProcess "mpv" ["--volume=130", "--", "deletion-warning.opus"]

        pure ()

getTTSApi :: IO (TTSReq -> IO BS.ByteString)
getTTSApi = do
    apiKey <- BS.filter (/= fromIntegral (ord '\n')) <$> BS.readFile "openai-api-key"

    return $ \req -> do
        rq <- CL.parseRequest "https://api.openai.com/v1/audio/speech"
            <&> CL.setRequestMethod "POST"
            <&> CL.setRequestBodyJSON req
            <&> CL.setRequestBearerAuth apiKey
        CL.getResponseBody <$> CL.httpBS rq

getGitlabApi :: IO (String -> IO CommitInfoLong)
getGitlabApi = do
    apiKey <- BS.filter (/= fromIntegral (ord '\n')) <$> BS.readFile "gitlab-api-key"

    return $ \commitHash -> do
        rq <- CL.parseRequest ("https://cau-git.rz.uni-kiel.de/api/v4/projects/3308/repository/commits/" <> commitHash)
            <&> CL.addRequestHeader "private-token" apiKey
        CL.getResponseBody <$> CL.httpJSON rq

main :: IO ()
main = do
    tts <- getTTSApi
    glApi <- getGitlabApi
    warp 1234 $ RepoAlarm tts glApi
