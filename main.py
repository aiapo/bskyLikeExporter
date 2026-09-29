from atproto import Client, AtUri, models, exceptions
import dominate
from dominate.tags import *
import requests
import os
from dotenv import load_dotenv
from m3u8_To_MP4 import multithread_download

BSKY_APP = "bsky.app"
BSKY_IMG_U = "https://cdn."+BSKY_APP+"/img/feed_fullsize/plain/"
BSKY_VID_U = "https://video."+BSKY_APP+"/watch/"

def getPost(did: str, rKey: str, client):
    try:
        post = client.get_post(rKey,did).value

        with div() as card:
            with blockquote():
                p(post.text)
                if post.embed is not None:
                    getEmbedded(post.embed,did,client)
            with div(cls='tags'):
                span("Posted at "+post.created_at,cls='tag')
                a("Link",href="https://"+BSKY_APP+"/profile/"+did+"/post/"+rKey,cls='tag')
                if post.reply is not None:
                    span("Reply to "+post.reply.parent.uri,cls='tag')

        return card
    except exceptions.BadRequestError as e:
        if e.response is not None:
            errorContent = e.response.content
            if errorContent.error == "RecordNotFound":
                return em("The post at "+rKey+" was deleted.")
            elif errorContent.error == "InvalidRequest" and errorContent.message.startswith("Could not find repo:"):
                return em("The post at "+rKey+" is inaccessible because the account is disabled/deleted/banned.")
        return em("The post at "+rKey+" couldn't be fetched. Trace: "+str(e))
    except Exception as e:
        print(e)
        return em("The post at "+rKey+" couldn't be fetched. Trace: "+str(e))

def getPoster(did: str, client):
    try: 
        profile = client.app.bsky.actor.get_profile({"actor":did})

        if not os.path.isfile('images/'+did+'.webp'):
            data = requests.get(profile.avatar).content
            with open('images/'+did+'.webp',"wb") as f:
                f.write(data)

        with div() as card:
            img(src="images/"+did+'.webp',originalsrc=profile.avatar,cls="avatar",loading="lazy")
            with a(href="https://"+BSKY_APP+"/profile/"+did,cls="tooltip"):
                span(str(profile.display_name or ''))
                span("| @"+str(profile.handle or ''))
                span(str(profile.description or ''),cls="tooltiptext")       

        return card
    except Exception as e:
        print(e)
        return p(did)
    
def getRecord(did: str, rKey: str, client):
    with div() as card:
        with div(cls='card-header'):
            with div(cls='card-header-title'):
                getPoster(did,client)
        with div(cls='card-content'):
            with div(cls='content'):
                getPost(did,rKey,client)

    return card

def parseAtUri(uri):
    return AtUri.from_str(uri).host, AtUri.from_str(uri).rkey

def downloadImage(did,cid):
    if not os.path.isfile('images/'+did+cid+'.webp'):
        data = requests.get(BSKY_IMG_U+did+"/"+cid).content
        with open('images/'+did+cid+'.webp', "wb") as f:
            f.write(data)

def getImages(did,images):
    with div() as card:
        for image in images:
            cid = str(image.image.cid)
            downloadImage(did,cid)
            img(src="images/"+did+cid+'.webp',originalsrc=BSKY_IMG_U+did+"/"+cid,alt=image.alt,title=image.alt,loading="lazy")

    return card

def getVideo(did,cid):
    fileName = did.replace(":","")+cid
    if not os.path.isfile("videos/"+fileName+".mp4"):
        multithread_download(m3u8_uri=BSKY_VID_U+did+"/"+cid+"/playlist.m3u8",mp4_file_dir="videos",mp4_file_name=fileName)

    return video(src="videos/"+fileName+".mp4",controls="true")

def getExternal(did,external):
    cid = str(external.thumb.cid)
    downloadImage(did, cid)
    with a(href=external.uri) as card:
        img(src='images/'+did+cid+'.webp',originalsrc=BSKY_IMG_U+did+"/"+cid,loading="lazy")
        h6(external.title)
        p(external.description)

    return card

def getEmbeddedRecord(uri,client):
    did, rKey = parseAtUri(uri)
    getRecord(did,rKey,client)

def getEmbedded(embedded,did,client):
    with div() as card:
        if embedded.__module__ == models.AppBskyEmbedImages.__name__:
            getImages(did,embedded.images)
        elif embedded.__module__ == models.AppBskyEmbedRecordWithMedia.__name__:
            getEmbedded(embedded.media,did,client)
            getEmbeddedRecord(embedded.record.record.uri,client)
        elif embedded.__module__ == models.AppBskyEmbedVideo.__name__:
            getVideo(did,str(embedded.video.cid))
        elif embedded.__module__ == models.AppBskyEmbedExternal.__name__:
            getExternal(did,embedded.external)
        elif embedded.__module__ == models.AppBskyEmbedRecord.__name__:
            getEmbeddedRecord(embedded.record.uri,client)
        elif embedded.__module__ == models.AppBskyEmbedGallery.__name__:
            getImages(did,embedded.items)

    return card

def main():
    load_dotenv()
    HANDLE = os.getenv('BSKY_HANDLE')
    PASSWORD = os.getenv('BSKY_APP_PASSWORD')

    if not os.path.isdir('images'):
        os.mkdir('images')
    if not os.path.isdir('videos'):
        os.mkdir('videos')

    if (HANDLE == "" or PASSWORD == "") or not os.path.isfile('.env'):
        print("You must fill out your handle and app password in .env before using... exiting...")
        exit()

    client = Client()
    client.login(HANDLE,PASSWORD)

    cursor = ""

    doc = dominate.document(title='Bluesky Like Export for '+client.me.display_name)
    with doc.head:
        link(rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.2/css/bulma.min.css')
        link(rel='stylesheet', href='style.css')
    with doc:
        with div(cls='container'):
            while True:
                likes = client.app.bsky.feed.like.list(client.me.did,limit=100,cursor=cursor)
                
                for item in likes.records.items():
                    likeRecord = item[1]
                    did, rKey = parseAtUri(likeRecord.subject.uri)

                    with div(cls='card'):
                        getRecord(did,rKey,client)
                        with div(cls='card-content'):
                            span("Liked at "+likeRecord.created_at,cls='tag')

                if likes.cursor is None:
                    break
                else:
                    print("[INFO][Cursor] Old: "+cursor+" / New: "+likes.cursor)
                    cursor = likes.cursor
                                
    with open("likes.html","w") as f:
        f.write(doc.render())

if __name__ == '__main__':
    main()